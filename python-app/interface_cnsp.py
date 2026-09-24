import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import serial
import threading
import os
import sys
import csv
from datetime import datetime

from cnsp_parser import decoder_trame, verifier_checksum, FRAME_SIZE, START_BYTE
from database import init_database, ajouter_evenement, lire_historique

# ================= CONFIG =================

PORT = os.getenv("CNSP_SERIAL_PORT", "COM7")
BAUDRATE = 115200
COMM_TIMEOUT_MS = 5000
LOGO_FILE = "project_logo.png"

# Compte de démonstration uniquement. Les valeurs peuvent être remplacées
# par des variables d'environnement sans modifier le code source.
AUTH_USER = os.getenv("CNSP_DEMO_USER", "demo")
AUTH_PASSWORD = os.getenv("CNSP_DEMO_PASSWORD", "demo")
CURRENT_USER = os.getenv("CNSP_DISPLAY_USER", "Demo User")

SYSTEMES = ["DME", "ILS_LOCALIZER", "GLIDE_SLOPE", "VHF", "ADS_B", "ONDULEUR"]

DISPLAY = {
    "DME": "DME",
    "ILS_LOCALIZER": "ILS LOCALIZER",
    "GLIDE_SLOPE": "GLIDE SLOPE",
    "VHF": "VHF",
    "ADS_B": "ADS-B",
    "ONDULEUR": "ONDULEUR"
}

TYPES = {
    "DME": "Navigation",
    "ILS_LOCALIZER": "Navigation",
    "GLIDE_SLOPE": "Navigation",
    "VHF": "Communication",
    "ADS_B": "Surveillance",
    "ONDULEUR": "Énergie"
}

FREQS = {
    "DME": "Canal de démonstration",
    "ILS_LOCALIZER": "Fréquence représentative",
    "GLIDE_SLOPE": "Fréquence représentative",
    "VHF": "Fréquence représentative",
    "ADS_B": "1090 MHz",
    "ONDULEUR": "230 VAC"
}

COULEURS = {
    "NORMAL": "#22c55e",
    "WARNING": "#f59e0b",
    "ALARME": "#ef4444",
    "HORS_SERVICE": "#64748b"
}

BG = "#020617"
PANEL = "#0f172a"
PANEL2 = "#111827"
BORDER = "#1e293b"
TEXT = "#e5e7eb"
MUTED = "#94a3b8"
BLUE = "#2563eb"

DEFAUTS = {s: "OK" for s in SYSTEMES}
ETATS = {s: "NORMAL" for s in SYSTEMES}

last_frame_time = None
trames_recues = 0
checksum_ok_count = 0
last_trame_brute = "--"
last_decode_text = "En attente d'une trame CNSP..."
app_started = False

# ================= DATABASE =================

init_database()

# ================= RESSOURCES =================

def resource_path(relative_path):
    """Retourne le chemin correct en mode Python normal et en mode .exe PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ================= ROOT =================

root = tk.Tk()
root.title("CNS Supervision Prototype")
root.geometry("1500x930")
root.configure(bg=BG)
root.withdraw()

# Chargement du logo ONDA si le fichier est présent dans le dossier du projet
LOGO_FULL = None
LOGO_SIDEBAR = None
LOGO_LOGIN = None
try:
    LOGO_FULL = tk.PhotoImage(file=resource_path(LOGO_FILE))
    LOGO_SIDEBAR = LOGO_FULL.subsample(2, 2)
    LOGO_LOGIN = LOGO_FULL.subsample(2, 2)
except Exception:
    LOGO_FULL = None
    LOGO_SIDEBAR = None
    LOGO_LOGIN = None

# ================= MENU WINDOWS =================

def show_about():
    about = tk.Toplevel(root)
    about.title("À propos - Prototype de supervision CNS")
    about.geometry("520x520")
    about.configure(bg=BG)
    about.resizable(False, False)
    about.grab_set()

    about.update_idletasks()
    x = (about.winfo_screenwidth() // 2) - 260
    y = (about.winfo_screenheight() // 2) - 260
    about.geometry(f"520x520+{x}+{y}")

    panel = tk.Frame(about, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
    panel.pack(fill="both", expand=True, padx=18, pady=18)

    if LOGO_FULL is not None:
        tk.Label(panel, image=LOGO_FULL, bg=PANEL).pack(pady=(18, 8))
    else:
        tk.Label(panel, text="CNS PROTOTYPE", fg="white", bg=PANEL, font=("Arial", 24, "bold")).pack(pady=(24, 8))

    tk.Label(panel, text="Plateforme de supervision CNS", fg="white", bg=PANEL, font=("Arial", 16, "bold")).pack(pady=(4, 8))
    tk.Label(panel, text="Version 1.0", fg="#60a5fa", bg=PANEL, font=("Consolas", 11, "bold")).pack()

    info_text = (
        "\nPrototype de supervision centralisée des équipements CNS\n\n"
        "Communication : STM32 + UART\n"
        "Protocole : CNSP v1\n"
        "Base de données : SQLite\n"
        "Interface : Application Windows Python/Tkinter\n\n"
        "Développé par : Hiba Sebbai\n"
        "Prototype réalisé dans le cadre d’un stage ONDA - Aéroport Fès-Saïss\n"
        "Données de démonstration / états représentatifs\n"
        "Année : 2026"
    )

    tk.Label(
        panel,
        text=info_text,
        fg="#cbd5e1",
        bg=PANEL,
        justify="center",
        font=("Arial", 10, "bold")
    ).pack(pady=10)

    tk.Button(
        panel,
        text="Fermer",
        command=about.destroy,
        bg=BLUE,
        fg="white",
        activebackground="#1d4ed8",
        activeforeground="white",
        relief="flat",
        font=("Arial", 10, "bold"),
        padx=28,
        pady=8
    ).pack(pady=(8, 18))


def show_configuration():
    config = tk.Toplevel(root)
    config.title("Configuration - Supervision CNS")
    config.geometry("500x430")
    config.configure(bg=BG)
    config.resizable(False, False)
    config.grab_set()

    config.update_idletasks()
    x = (config.winfo_screenwidth() // 2) - 250
    y = (config.winfo_screenheight() // 2) - 215
    config.geometry(f"500x430+{x}+{y}")

    panel = tk.Frame(config, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
    panel.pack(fill="both", expand=True, padx=18, pady=18)

    tk.Label(panel, text="Configuration de l'application", fg="white", bg=PANEL, font=("Arial", 16, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
    tk.Label(panel, text="Paramètres utilisés par le prototype de supervision", fg=MUTED, bg=PANEL, font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=(0, 16))

    form = tk.Frame(panel, bg=PANEL)
    form.pack(fill="x", padx=20)

    def config_row(label, value):
        row = tk.Frame(form, bg=PANEL)
        row.pack(fill="x", pady=6)
        tk.Label(row, text=label, fg=MUTED, bg=PANEL, font=("Arial", 10, "bold"), width=18, anchor="w").pack(side="left")
        entry = tk.Entry(row, font=("Consolas", 10, "bold"), bg="#020617", fg="white", insertbackground="white", relief="flat")
        entry.pack(side="left", fill="x", expand=True, ipady=6)
        entry.insert(0, str(value))
        entry.config(state="readonly", readonlybackground="#020617")
        return entry

    config_row("Port série", PORT)
    config_row("Baudrate", BAUDRATE)
    config_row("Timeout UART", f"{COMM_TIMEOUT_MS} ms")
    config_row("Utilisateur", CURRENT_USER)
    config_row("Protocole", "CNSP v1")
    config_row("Base locale", "SQLite / supervision.db")

    tk.Label(
        panel,
        text="Remarque : dans cette version prototype, les paramètres sont fixés dans le fichier de configuration du logiciel.",
        fg="#f59e0b",
        bg=PANEL,
        wraplength=430,
        justify="left",
        font=("Arial", 9, "bold")
    ).pack(anchor="w", padx=20, pady=(18, 10))

    tk.Button(
        panel,
        text="Fermer",
        command=config.destroy,
        bg=BLUE,
        fg="white",
        activebackground="#1d4ed8",
        activeforeground="white",
        relief="flat",
        font=("Arial", 10, "bold"),
        padx=28,
        pady=8
    ).pack(pady=(6, 16))



def exporter_historique_csv():
    try:
        events = lire_historique()
        if not events:
            messagebox.showinfo("Export CSV", "Aucun événement à exporter.")
            return

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"Historique_CNS_{now}.csv"

        file_path = filedialog.asksaveasfilename(
            title="Exporter l'historique en CSV",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("Fichier CSV", "*.csv")]
        )

        if not file_path:
            return

        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["Date / Heure", "Compteur", "Système", "Défaut", "État"])
            for event in events:
                writer.writerow(event)

        messagebox.showinfo("Export CSV", f"Historique exporté avec succès :\n{file_path}")

    except Exception as e:
        messagebox.showerror("Erreur export CSV", f"Impossible d'exporter l'historique :\n{e}")


def exporter_historique_pdf():
    try:
        events = lire_historique()
        if not events:
            messagebox.showinfo("Export PDF", "Aucun événement à exporter.")
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm
        except Exception:
            messagebox.showwarning(
                "ReportLab manquant",
                "Pour exporter en PDF, installe d'abord ReportLab :\n\npip install reportlab"
            )
            return

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"Rapport_CNS_{now}.pdf"

        file_path = filedialog.asksaveasfilename(
            title="Exporter l'historique en PDF",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("Fichier PDF", "*.pdf")]
        )

        if not file_path:
            return

        c = canvas.Canvas(file_path, pagesize=A4)
        width, height = A4

        y = height - 2 * cm
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2 * cm, y, "Rapport d'historique - Supervision CNS")
        y -= 0.7 * cm

        c.setFont("Helvetica", 10)
        c.drawString(2 * cm, y, f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        y -= 0.5 * cm
        c.drawString(2 * cm, y, "Application : Prototype de supervision CNS")
        y -= 0.9 * cm

        c.setFont("Helvetica-Bold", 9)
        headers = ["Date / Heure", "Compteur", "Système", "Défaut", "État"]
        x_positions = [1.5 * cm, 6.0 * cm, 8.0 * cm, 11.0 * cm, 16.0 * cm]

        for x, h in zip(x_positions, headers):
            c.drawString(x, y, h)
        y -= 0.35 * cm
        c.line(1.5 * cm, y, 19.5 * cm, y)
        y -= 0.35 * cm

        c.setFont("Helvetica", 8)

        for event in events:
            if y < 2 * cm:
                c.showPage()
                y = height - 2 * cm
                c.setFont("Helvetica-Bold", 9)
                for x, h in zip(x_positions, headers):
                    c.drawString(x, y, h)
                y -= 0.35 * cm
                c.line(1.5 * cm, y, 19.5 * cm, y)
                y -= 0.35 * cm
                c.setFont("Helvetica", 8)

            date_heure, compteur, systeme, defaut, etat = event

            values = [
                str(date_heure)[:22],
                str(compteur),
                str(systeme)[:18],
                str(defaut)[:24],
                str(etat)
            ]

            for x, value in zip(x_positions, values):
                c.drawString(x, y, value)

            y -= 0.32 * cm

        c.save()
        messagebox.showinfo("Export PDF", f"Rapport PDF exporté avec succès :\n{file_path}")

    except Exception as e:
        messagebox.showerror("Erreur export PDF", f"Impossible d'exporter le PDF :\n{e}")


def build_menu_bar():
    menubar = tk.Menu(root)

    menu_fichier = tk.Menu(menubar, tearoff=0)
    menu_fichier.add_command(label="Quitter", command=root.destroy)
    menubar.add_cascade(label="Fichier", menu=menu_fichier)

    menu_outils = tk.Menu(menubar, tearoff=0)
    menu_outils.add_command(label="Configuration", command=show_configuration)
    menu_outils.add_separator()
    menu_outils.add_command(label="Exporter historique CSV", command=exporter_historique_csv)
    menu_outils.add_command(label="Exporter historique PDF", command=exporter_historique_pdf)
    menubar.add_cascade(label="Outils", menu=menu_outils)

    menu_aide = tk.Menu(menubar, tearoff=0)
    menu_aide.add_command(label="À propos", command=show_about)
    menubar.add_cascade(label="Aide", menu=menu_aide)

    root.config(menu=menubar)


build_menu_bar()


# ================= HELPERS =================

def clear_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()

def normaliser_etat(etat):
    if etat is None:
        return "NORMAL"

    e = str(etat).strip().upper()
    e = e.replace(" ", "_").replace("-", "_")

    if e in ["NORMAL", "OK"]:
        return "NORMAL"
    if e in ["WARNING", "WARN", "AVERTISSEMENT"]:
        return "WARNING"
    if e in ["ALARME", "ALARM"]:
        return "ALARME"
    if e in ["HORS_SERVICE", "HS"]:
        return "HORS_SERVICE"

    return e


def state_counts():
    normalises = [normaliser_etat(e) for e in ETATS.values()]

    ok = sum(1 for e in normalises if e == "NORMAL")
    warnings = sum(1 for e in normalises if e == "WARNING")
    alarmes = sum(1 for e in normalises if e == "ALARME")
    hors_service = sum(1 for e in normalises if e == "HORS_SERVICE")

    return ok, warnings, alarmes, hors_service

def fault_color(defaut, etat):
    if etat == "NORMAL" and defaut == "OK":
        return COULEURS["NORMAL"]
    return COULEURS.get(etat, TEXT)

def make_title(parent, title, subtitle=None):
    tk.Label(parent, text=title, fg="white", bg=BG, font=("Arial", 18, "bold")).pack(anchor="w")
    if subtitle:
        tk.Label(parent, text=subtitle, fg=MUTED, bg=BG, font=("Arial", 10, "bold")).pack(anchor="w", pady=(2, 14))
    else:
        tk.Frame(parent, bg=BG, height=12).pack()

def make_panel(parent, **pack_opts):
    panel = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
    panel.pack(**pack_opts)
    return panel

# ================= MAIN LAYOUT =================

sidebar = tk.Frame(root, bg=PANEL, width=245)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

main = tk.Frame(root, bg=BG)
main.pack(side="left", fill="both", expand=True)

topbar = tk.Frame(main, bg=PANEL, height=62)
topbar.pack(fill="x")
topbar.pack_propagate(False)

label_page_title = tk.Label(topbar, text="Tableau de bord", fg="white", bg=PANEL, font=("Arial", 17, "bold"))
label_page_title.pack(side="left", padx=24)

label_top_status = tk.Label(topbar, text="STM32 : attente", fg="#f59e0b", bg="#1e293b", font=("Arial", 11, "bold"), padx=14, pady=7)
label_top_status.pack(side="right", padx=14)

btn_logout = tk.Button(topbar, text="Déconnexion", fg="white", bg="#334155", activebackground="#475569", activeforeground="white", relief="flat", font=("Arial", 10, "bold"), padx=12, pady=6)
btn_logout.pack(side="right", padx=(0, 8))

label_user = tk.Label(topbar, text="Utilisateur : --", fg="#cbd5e1", bg=PANEL, font=("Arial", 10, "bold"))
label_user.pack(side="right", padx=12)

label_time = tk.Label(topbar, text="--", fg="#60a5fa", bg=PANEL, font=("Consolas", 12, "bold"))
label_time.pack(side="right", padx=20)

content = tk.Frame(main, bg=BG)
content.pack(fill="both", expand=True, padx=22, pady=18)

# status bar
status_bar = tk.Frame(main, bg="#0f172a", height=28)
status_bar.pack(fill="x", side="bottom")
status_bar.pack_propagate(False)

label_status_uart = tk.Label(status_bar, text=f"UART {PORT} · {BAUDRATE} bauds", fg="#38bdf8", bg="#0f172a", font=("Consolas", 9, "bold"))
label_status_uart.pack(side="left", padx=15)

label_status_db = tk.Label(status_bar, text="SQLite OK", fg="#22c55e", bg="#0f172a", font=("Consolas", 9, "bold"))
label_status_db.pack(side="left", padx=15)

label_status_checksum = tk.Label(status_bar, text="Checksum : --", fg="#94a3b8", bg="#0f172a", font=("Consolas", 9, "bold"))
label_status_checksum.pack(side="left", padx=15)

label_status_frames = tk.Label(status_bar, text="Trames reçues : 0", fg="#a78bfa", bg="#0f172a", font=("Consolas", 9, "bold"))
label_status_frames.pack(side="left", padx=15)

label_status_comm = tk.Label(status_bar, text="Communication : attente", fg="#f59e0b", bg="#0f172a", font=("Consolas", 9, "bold"))
label_status_comm.pack(side="right", padx=15)

# ================= SIDEBAR =================

if LOGO_SIDEBAR is not None:
    tk.Label(sidebar, image=LOGO_SIDEBAR, bg=PANEL).pack(anchor="w", padx=22, pady=(20, 6))
else:
    tk.Label(sidebar, text="CNS", fg="white", bg=PANEL, font=("Arial", 26, "bold")).pack(anchor="w", padx=22, pady=(22, 0))

tk.Label(sidebar, text="Prototype · Supervision CNS", fg=MUTED, bg=PANEL, font=("Arial", 11, "bold")).pack(anchor="w", padx=24, pady=(0, 4))
tk.Label(sidebar, text="Données représentatives de démonstration", fg="#64748b", bg=PANEL, font=("Arial", 10)).pack(anchor="w", padx=24, pady=(0, 28))

menu_buttons = {}
current_page = "dashboard"

def set_active_menu(page):
    for p, btn in menu_buttons.items():
        if p == page:
            btn.config(bg=BLUE, fg="white")
        else:
            btn.config(bg=PANEL, fg=MUTED)

def make_menu_button(page, text):
    btn = tk.Button(sidebar, text=text, command=lambda: show_page(page), fg=MUTED, bg=PANEL, activebackground=BLUE, activeforeground="white", relief="flat", anchor="w", padx=18, pady=11, font=("Arial", 12, "bold"))
    btn.pack(fill="x", padx=14, pady=4)
    menu_buttons[page] = btn

make_menu_button("dashboard", "▦  Tableau de bord")
make_menu_button("equipements", "◉  Équipements")
make_menu_button("alarmes", "⚠  Alarmes")
make_menu_button("protocole", "▣  Protocole CNSP")
make_menu_button("historique", "▤  Historique")

# technical state

tk.Label(sidebar, text="ÉTAT TECHNIQUE", fg="#64748b", bg=PANEL, font=("Arial", 10, "bold")).pack(anchor="w", padx=24, pady=(60, 8))
label_side_stm32 = tk.Label(sidebar, text="● STM32 : attente", fg="#f59e0b", bg=PANEL, font=("Arial", 10, "bold"))
label_side_stm32.pack(anchor="w", padx=24, pady=4)
label_side_uart = tk.Label(sidebar, text=f"● UART : {BAUDRATE} bauds", fg="#38bdf8", bg=PANEL, font=("Arial", 10, "bold"))
label_side_uart.pack(anchor="w", padx=24, pady=4)
label_side_db = tk.Label(sidebar, text="● SQLite : connectée", fg="#22c55e", bg=PANEL, font=("Arial", 10, "bold"))
label_side_db.pack(anchor="w", padx=24, pady=4)
label_side_proto = tk.Label(sidebar, text="● CNSP v1 : actif", fg="#a78bfa", bg=PANEL, font=("Arial", 10, "bold"))
label_side_proto.pack(anchor="w", padx=24, pady=4)

tk.Label(sidebar, text="Prototype embarqué STM32\nTrames binaires + checksum\nHistorisation SQLite", fg="#64748b", bg=PANEL, justify="left", font=("Arial", 9)).pack(side="bottom", anchor="w", padx=24, pady=25)

# ================= SHARED WIDGET REFERENCES =================

cards = {}
canvas_donut = None
recent_list = None
table_hist = None
label_analyse = None
health_canvas = None
page_alarm_table = None
page_equipment_table = None
page_history_table = None
page_protocol_label = None

# ================= PAGES =================

def create_kpis(parent):
    kpi_frame = tk.Frame(parent, bg=BG)
    kpi_frame.pack(fill="x")
    labels = {}

    def make_kpi(title, value, color, key):
        box = tk.Frame(kpi_frame, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, height=92)
        box.pack(side="left", padx=8, fill="x", expand=True)
        box.pack_propagate(False)
        tk.Label(box, text=title, fg=MUTED, bg=PANEL, font=("Arial", 10, "bold")).pack(anchor="w", padx=18, pady=(13, 0))
        lbl = tk.Label(box, text=value, fg=color, bg=PANEL, font=("Arial", 26, "bold"))
        lbl.pack(anchor="w", padx=18)
        labels[key] = lbl

    make_kpi("SYSTÈMES SUPERVISÉS", "6", "#60a5fa", "total")
    make_kpi("OPÉRATIONNELS", "6", "#22c55e", "ok")
    make_kpi("WARNINGS", "0", "#f59e0b", "warning")
    make_kpi("ALARMES", "0", "#ef4444", "alarme")
    make_kpi("TRAMES REÇUES", "0", "#a78bfa", "frames")
    return labels

kpi_labels = {}

def create_equipment_card(parent, systeme, row, col):
    card = tk.Frame(parent, bg=PANEL, highlightbackground=COULEURS["NORMAL"], highlightthickness=3, width=255, height=150)
    card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
    card.grid_propagate(False)

    tk.Label(card, text=DISPLAY[systeme], fg="white", bg=PANEL, font=("Arial", 13, "bold")).place(x=14, y=12)
    tk.Label(card, text=TYPES[systeme], fg="#64748b", bg=PANEL, font=("Arial", 8, "bold")).place(x=14, y=36)

    status = tk.Label(card, text="NORMAL", fg=COULEURS["NORMAL"], bg=PANEL, font=("Arial", 11, "bold"))
    status.place(x=14, y=60)
    fault = tk.Label(card, text="Défaut : OK", fg="#cbd5e1", bg=PANEL, font=("Arial", 9, "bold"))
    fault.place(x=14, y=88)
    freq = tk.Label(card, text=FREQS[systeme], fg="#38bdf8", bg=PANEL, font=("Arial", 9, "bold"))
    freq.place(x=14, y=116)

    def led(text, x, y):
        lbl = tk.Label(card, text=f"● {text}", fg="#22c55e", bg=PANEL, font=("Arial", 8, "bold"))
        lbl.place(x=x, y=y)
        return lbl

    tx1 = led("TX1", 165, 24)
    tx2 = led("TX2", 215, 24)
    m1 = led("MAINS1", 165, 54)
    m2 = led("MAINS2", 165, 76)
    comm = led("COMM", 165, 108)

    cards[systeme] = {"frame": card, "status": status, "fault": fault, "freq": freq, "tx1": tx1, "tx2": tx2, "m1": m1, "m2": m2, "comm": comm}
    refresh_one_card(systeme)


def show_dashboard():
    global canvas_donut, recent_list, table_hist, label_analyse, health_canvas, kpi_labels
    clear_frame(content)
    label_page_title.config(text="Plateforme de supervision CNS")
    make_title(content, "Tableau de bord de supervision CNS", "Vue temps réel des systèmes CNS et de la communication CNSP")
    kpi_labels = create_kpis(content)

    health = make_panel(content, fill="x", pady=(8, 6))
    tk.Label(health, text="SANTÉ DU PROTOCOLE CNSP", fg="white", bg=PANEL, font=("Arial", 11, "bold")).pack(anchor="w", padx=14, pady=(10, 0))
    health_canvas = tk.Canvas(health, height=58, bg=PANEL, highlightthickness=0)
    health_canvas.pack(fill="x", padx=12, pady=6)

    middle = tk.Frame(content, bg=BG)
    middle.pack(fill="both", expand=True, pady=4)
    left_area = tk.Frame(middle, bg=BG)
    left_area.pack(side="left", fill="both", expand=True)
    right_area = tk.Frame(middle, bg=BG, width=390)
    right_area.pack(side="right", fill="y", padx=(18, 0))
    right_area.pack_propagate(False)

    tk.Label(left_area, text="ÉTAT OPÉRATIONNEL DES ÉQUIPEMENTS", fg=MUTED, bg=BG, font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 8))
    cards_frame = tk.Frame(left_area, bg=BG)
    cards_frame.pack(fill="x")
    cards.clear()
    for i, sys in enumerate(SYSTEMES):
        create_equipment_card(cards_frame, sys, i // 3, i % 3)

    panel_donut = make_panel(right_area, fill="x", pady=(0, 14))
    panel_donut.config(height=270)
    panel_donut.pack_propagate(False)
    tk.Label(panel_donut, text="RÉPARTITION DES ÉTATS", fg="white", bg=PANEL, font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(14, 0))
    canvas_donut = tk.Canvas(panel_donut, width=360, height=210, bg=PANEL, highlightthickness=0)
    canvas_donut.pack(pady=5)

    panel_alarm = make_panel(right_area, fill="both", expand=True)
    tk.Label(panel_alarm, text="ALARMES RÉCENTES", fg="white", bg=PANEL, font=("Arial", 12, "bold")).pack(anchor="w", padx=15, pady=(14, 0))
    recent_list = tk.Listbox(panel_alarm, bg="#020617", fg="#e2e8f0", font=("Consolas", 9), height=15, bd=0, highlightthickness=0, selectbackground="#1d4ed8")
    recent_list.pack(fill="both", expand=True, padx=12, pady=12)

    bottom = tk.Frame(content, bg=BG)
    bottom.pack(fill="x", pady=(0, 0))
    hist_panel = make_panel(bottom, side="left", fill="both", expand=True, padx=(0, 12))
    tk.Label(hist_panel, text="HISTORIQUE DES ÉVÉNEMENTS", fg="white", bg=PANEL, font=("Arial", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
    table_hist = make_tree(hist_panel, height=6)
    table_hist.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    analyse_panel = make_panel(bottom, side="right", fill="both")
    analyse_panel.config(width=455)
    analyse_panel.pack_propagate(False)
    tk.Label(analyse_panel, text="ANALYSEUR DU PROTOCOLE CNSP", fg="white", bg=PANEL, font=("Arial", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
    label_analyse = tk.Label(analyse_panel, text=last_decode_text, fg="#e2e8f0", bg="#020617", font=("Consolas", 9, "bold"), justify="left", anchor="nw", padx=12, pady=10)
    label_analyse.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    update_all_ui()


def make_tree(parent, height=10):
    colonnes = ("date", "compteur", "systeme", "defaut", "etat")
    tree = ttk.Treeview(parent, columns=colonnes, show="headings", height=height)
    for col, title, width in [("date", "Date / Heure", 165), ("compteur", "Compteur", 80), ("systeme", "Système", 130), ("defaut", "Défaut", 180), ("etat", "État", 110)]:
        tree.heading(col, text=title)
        tree.column(col, width=width)
    tree.tag_configure("NORMAL", foreground="#22c55e")
    tree.tag_configure("WARNING", foreground="#f59e0b")
    tree.tag_configure("ALARME", foreground="#ef4444")
    tree.tag_configure("HORS_SERVICE", foreground="#94a3b8")
    return tree


def fill_tree(tree, alarm_only=False):
    if tree is None:
        return
    for row in tree.get_children():
        tree.delete(row)
    try:
        for event in lire_historique():
            date_heure, compteur, systeme, defaut, etat = event
            if alarm_only and etat not in ["WARNING", "ALARME", "HORS_SERVICE"]:
                continue
            tree.insert("", "end", values=(date_heure, compteur, systeme, defaut, etat), tags=(etat,))
    except Exception:
        pass


def show_equipements():
    global page_equipment_table
    clear_frame(content)
    label_page_title.config(text="Équipements")
    make_title(content, "Équipements supervisés", "Vue détaillée des systèmes CNS suivis par l'application")

    panel = make_panel(content, fill="both", expand=True)
    cols = ("systeme", "nom", "type", "frequence", "etat", "defaut")
    page_equipment_table = ttk.Treeview(panel, columns=cols, show="headings", height=18)
    for col, title, width in [("systeme", "Code", 130), ("nom", "Nom", 180), ("type", "Type", 150), ("frequence", "Fréquence/Canal", 150), ("etat", "État", 130), ("defaut", "Défaut", 220)]:
        page_equipment_table.heading(col, text=title)
        page_equipment_table.column(col, width=width)
    page_equipment_table.pack(fill="both", expand=True, padx=14, pady=14)
    update_equipment_page()


def update_equipment_page():
    if page_equipment_table is None:
        return
    for row in page_equipment_table.get_children():
        page_equipment_table.delete(row)
    for s in SYSTEMES:
        page_equipment_table.insert("", "end", values=(s, DISPLAY[s], TYPES[s], FREQS[s], ETATS[s], DEFAUTS[s]))


def show_alarm_page():
    global page_alarm_table
    clear_frame(content)
    label_page_title.config(text="Alarmes")
    make_title(content, "Alarmes et événements critiques", "Liste filtrée des warnings, alarmes et hors service")
    panel = make_panel(content, fill="both", expand=True)
    page_alarm_table = make_tree(panel, height=20)
    page_alarm_table.pack(fill="both", expand=True, padx=14, pady=14)
    fill_tree(page_alarm_table, alarm_only=True)


def show_protocole():
    global page_protocol_label
    clear_frame(content)
    label_page_title.config(text="Protocole CNSP")
    make_title(content, "Analyse du protocole CNSP v1", "Trame binaire, décodage et contrôle d'intégrité")
    panel = make_panel(content, fill="both", expand=True)
    page_protocol_label = tk.Label(panel, text=last_decode_text, fg="#e2e8f0", bg="#020617", font=("Consolas", 12, "bold"), justify="left", anchor="nw", padx=20, pady=20)
    page_protocol_label.pack(fill="both", expand=True, padx=18, pady=18)


def show_historique():
    global page_history_table
    clear_frame(content)
    label_page_title.config(text="Historique")
    make_title(content, "Historique SQLite", "Tous les événements enregistrés dans la base locale")
    panel = make_panel(content, fill="both", expand=True)
    actions = tk.Frame(panel, bg=PANEL)
    actions.pack(fill="x", padx=14, pady=(12, 0))

    tk.Button(
        actions,
        text="Exporter CSV",
        command=exporter_historique_csv,
        bg=BLUE,
        fg="white",
        activebackground="#1d4ed8",
        activeforeground="white",
        relief="flat",
        font=("Arial", 10, "bold"),
        padx=14,
        pady=6
    ).pack(side="left", padx=(0, 8))

    tk.Button(
        actions,
        text="Exporter PDF",
        command=exporter_historique_pdf,
        bg="#334155",
        fg="white",
        activebackground="#475569",
        activeforeground="white",
        relief="flat",
        font=("Arial", 10, "bold"),
        padx=14,
        pady=6
    ).pack(side="left")

    page_history_table = make_tree(panel, height=20)
    page_history_table.pack(fill="both", expand=True, padx=14, pady=14)
    fill_tree(page_history_table, alarm_only=False)


def show_page(page):
    global current_page
    current_page = page
    set_active_menu(page)
    if page == "dashboard":
        show_dashboard()
    elif page == "equipements":
        show_equipements()
    elif page == "alarmes":
        show_alarm_page()
    elif page == "protocole":
        show_protocole()
    elif page == "historique":
        show_historique()

# ================= STYLE =================

style = ttk.Style()
style.theme_use("default")
style.configure("Treeview", background="#020617", foreground="#e5e7eb", fieldbackground="#020617", rowheight=25, bordercolor="#1e293b", borderwidth=0, font=("Arial", 9))
style.configure("Treeview.Heading", background="#1e293b", foreground="white", font=("Arial", 9, "bold"))
style.map("Treeview", background=[("selected", "#1d4ed8")])

# ================= UI UPDATE =================

def update_clock():
    now = datetime.now()
    label_time.config(text=now.strftime("%d/%m/%Y · %H:%M:%S"))
    root.after(1000, update_clock)

def set_comm_connected():
    label_top_status.config(text="STM32 : CONNECTÉE", fg="#22c55e")
    label_side_stm32.config(text="● STM32 : connectée", fg="#22c55e")
    label_status_comm.config(text="Communication : OK", fg="#22c55e")

def set_comm_waiting():
    label_top_status.config(text="STM32 : attente", fg="#f59e0b")
    label_side_stm32.config(text="● STM32 : attente", fg="#f59e0b")
    label_status_comm.config(text="Communication : attente", fg="#f59e0b")

def set_comm_lost():
    label_top_status.config(text="STM32 : COMMUNICATION PERDUE", fg="#ef4444")
    label_side_stm32.config(text="● STM32 : communication perdue", fg="#ef4444")
    label_status_comm.config(text="Communication : perdue", fg="#ef4444")
    for s in SYSTEMES:
        if s in cards:
            cards[s]["comm"].config(fg="#ef4444")

def check_communication():
    if last_frame_time is not None:
        elapsed_ms = (datetime.now() - last_frame_time).total_seconds() * 1000
        if elapsed_ms > COMM_TIMEOUT_MS:
            set_comm_lost()
    root.after(1000, check_communication)

def draw_health():
    if health_canvas is None:
        return
    health_canvas.delete("all")
    comm_pct = 100
    if last_frame_time is not None:
        elapsed_ms = (datetime.now() - last_frame_time).total_seconds() * 1000
        comm_pct = max(0, min(100, int(100 - (elapsed_ms / COMM_TIMEOUT_MS) * 100)))
    checksum_pct = 100 if trames_recues == 0 else int((checksum_ok_count / trames_recues) * 100)
    availability = comm_pct
    items = [("Communication UART", comm_pct, "#38bdf8"), ("Checksum valide", checksum_pct, "#22c55e"), ("Disponibilité", availability, "#a78bfa")]
    x = 20
    y = 10
    for label, pct, color in items:
        health_canvas.create_text(x, y, text=label, fill=MUTED, anchor="nw", font=("Arial", 9, "bold"))
        health_canvas.create_rectangle(x, y + 20, x + 260, y + 34, fill="#1e293b", outline="#1e293b")
        health_canvas.create_rectangle(x, y + 20, x + int(260 * pct / 100), y + 34, fill=color, outline=color)
        health_canvas.create_text(x + 275, y + 27, text=f"{pct}%", fill="white", anchor="w", font=("Arial", 9, "bold"))
        x += 390

def draw_donut():
    if canvas_donut is None:
        return

    canvas_donut.delete("all")

    ok, warning, alarm, hors_service = state_counts()
    total = max(ok + warning + alarm + hors_service, 1)

    data = [
        ("NORMAL", ok, "#22c55e"),
        ("WARNING", warning, "#f59e0b"),
        ("ALARME", alarm, "#ef4444"),
        ("HS", hors_service, "#64748b")
    ]

    x0, y0, x1, y1 = 25, 20, 185, 180
    cx = 105

    dominant = None
    for name, value, color in data:
        if value == total and total > 0:
            dominant = (name, value, color)
            break

    if dominant is not None:
        canvas_donut.create_oval(x0, y0, x1, y1, fill=dominant[2], outline=PANEL, width=2)
    else:
        start = 90
        for name, value, color in data:
            if value > 0:
                extent = -360 * value / total
                canvas_donut.create_arc(
                    x0, y0, x1, y1,
                    start=start,
                    extent=extent,
                    fill=color,
                    outline=PANEL,
                    width=2
                )
                start += extent

    canvas_donut.create_oval(68, 63, 142, 137, fill=PANEL, outline=PANEL)
    canvas_donut.create_text(cx, 95, text=str(total), fill="white", font=("Arial", 20, "bold"))
    canvas_donut.create_text(cx, 118, text="systèmes", fill=MUTED, font=("Arial", 8, "bold"))

    y = 25
    for name, value, color in data:
        canvas_donut.create_rectangle(205, y, 219, y + 14, fill=color, outline=color)
        canvas_donut.create_text(
            228,
            y + 7,
            text=f"{name} ({value})",
            fill="#cbd5e1",
            anchor="w",
            font=("Arial", 8, "bold")
        )
        y += 28

def refresh_one_card(systeme):
    if systeme not in cards:
        return
    etat = ETATS.get(systeme, "NORMAL")
    defaut = DEFAUTS.get(systeme, "OK")
    color = COULEURS.get(etat, "#64748b")
    c = cards[systeme]
    c["frame"].config(highlightbackground=color)
    c["status"].config(text=etat, fg=color)
    c["fault"].config(text=f"Défaut : {defaut}", fg=fault_color(defaut, etat))
    if etat == "NORMAL":
        vals = ["#22c55e", "#22c55e", "#22c55e", "#22c55e", "#22c55e"]
    elif etat == "WARNING":
        vals = ["#22c55e", "#f59e0b", "#22c55e", "#22c55e", "#f59e0b"]
    elif etat == "ALARME":
        vals = ["#ef4444", "#f59e0b", "#22c55e", "#ef4444", "#ef4444"]
    else:
        vals = ["#64748b", "#64748b", "#64748b", "#64748b", "#ef4444"]
    for key, val in zip(["tx1", "tx2", "m1", "m2", "comm"], vals):
        c[key].config(fg=val)

def update_all_ui():
    ok, warnings, alarmes, hs = state_counts()
    for key, value in [("total", len(SYSTEMES)), ("ok", ok), ("warning", warnings), ("alarme", alarmes), ("frames", trames_recues)]:
        if key in kpi_labels:
            kpi_labels[key].config(text=str(value))
    label_status_frames.config(text=f"Trames reçues : {trames_recues}")
    for s in SYSTEMES:
        refresh_one_card(s)
    draw_donut()
    draw_health()
    fill_tree(table_hist, False)
    fill_tree(page_alarm_table, True)
    fill_tree(page_history_table, False)
    update_equipment_page()
    if page_protocol_label is not None:
        page_protocol_label.config(text=last_decode_text)
    if label_analyse is not None:
        label_analyse.config(text=last_decode_text)

# ================= PROTOCOL PROCESSING =================

def add_recent_alarm(systeme, defaut, etat):
    if recent_list is None:
        return
    if etat not in ["WARNING", "ALARME", "HORS_SERVICE"]:
        return
    now = datetime.now().strftime("%H:%M:%S")
    prefix = "ROUGE" if etat == "ALARME" else "ORANGE" if etat == "WARNING" else "GRIS"
    text = f"{prefix} {now} | {etat:<12} | {systeme:<14} | {defaut}"
    recent_list.insert(0, text)
    if recent_list.size() > 16:
        recent_list.delete(16)

def build_analyse_text(trame, data):
    brute = " ".join(f"{b:02X}" for b in trame)
    checksum_calcule = sum(trame[:6]) & 0xFF
    checksum_recu = trame[6]
    valid = checksum_calcule == checksum_recu
    return (
        f"TRAME BRUTE\n{brute}\n\n"
        f"DÉCODAGE\n"
        f"START    : 0x{trame[0]:02X}\n"
        f"VERSION  : {trame[1]}\n"
        f"ADRESSE  : 0x{trame[2]:02X}  -> {data['systeme']}\n"
        f"DÉFAUT   : 0x{trame[3]:02X}  -> {data['defaut']}\n"
        f"ÉTAT     : 0x{trame[4]:02X}  -> {data['etat']}\n"
        f"COMPTEUR : {trame[5]}\n\n"
        f"INTÉGRITÉ\n"
        f"Reçu     : 0x{checksum_recu:02X}\n"
        f"Calculé  : 0x{checksum_calcule:02X}\n"
        f"Résultat : {'CHECKSUM VALIDE' if valid else 'CHECKSUM INVALIDE'}"
    )

def traiter_reception_cnsp(data, trame, checksum_ok):
    """Traite chaque trame candidate, y compris celles rejetées par le checksum."""
    global last_frame_time, trames_recues, checksum_ok_count, last_decode_text, last_trame_brute

    trames_recues += 1
    last_frame_time = datetime.now()
    last_trame_brute = " ".join(f"{b:02X}" for b in trame)
    set_comm_connected()

    if checksum_ok:
        checksum_ok_count += 1
        label_status_checksum.config(text="Checksum : OK", fg="#22c55e")
    else:
        label_status_checksum.config(text="Checksum : ERREUR", fg="#ef4444")
        last_decode_text = (
            f"TRAME REJETÉE\n{last_trame_brute}\n\n"
            "Motif : checksum invalide."
        )
        update_all_ui()
        return

    # Le checksum est valide, mais le décodeur peut encore rejeter la trame
    # (version non supportée, identifiant invalide, etc.).
    if data is None:
        last_decode_text = (
            f"TRAME REJETÉE\n{last_trame_brute}\n\n"
            "Motif : format ou version CNSP non supporté."
        )
        update_all_ui()
        return

    systeme = data["systeme"]
    if systeme == "INCONNU":
        last_decode_text = build_analyse_text(trame, data)
        update_all_ui()
        return

    DEFAUTS[systeme] = data["defaut"]
    ETATS[systeme] = data["etat"]
    last_decode_text = build_analyse_text(trame, data)
    add_recent_alarm(systeme, data["defaut"], data["etat"])

    try:
        ajouter_evenement(data["compteur"], systeme, data["defaut"], data["etat"])
        label_side_db.config(text="● SQLite : connectée", fg="#22c55e")
        label_status_db.config(text="SQLite OK", fg="#22c55e")
    except Exception:
        label_side_db.config(text="● SQLite : erreur", fg="#ef4444")
        label_status_db.config(text="SQLite ERREUR", fg="#ef4444")

    update_all_ui()

def lire_uart_cnsp():
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
        root.after(0, set_comm_waiting)
        buffer = bytearray()
        while True:
            b = ser.read(1)
            if not b:
                continue
            val = b[0]
            if len(buffer) == 0 and val != START_BYTE:
                continue
            buffer.append(val)
            if len(buffer) == FRAME_SIZE:
                trame = bytes(buffer)
                buffer.clear()
                checksum_ok = verifier_checksum(trame)
                data = decoder_trame(trame)
                root.after(0, traiter_reception_cnsp, data, trame, checksum_ok)
    except serial.SerialException:
        root.after(0, set_comm_lost)
        root.after(0, lambda: label_status_comm.config(text="Communication : port fermé", fg="#ef4444"))

# ================= LOGIN =================

def start_dashboard():
    global app_started
    root.deiconify()
    root.lift()
    root.focus_force()
    label_user.config(text=f"Utilisateur : {CURRENT_USER}")
    show_page("dashboard")
    if recent_list is not None and recent_list.size() == 0:
        recent_list.insert(0, f"SESSION {datetime.now().strftime('%H:%M:%S')} | Connexion | {CURRENT_USER}")
    if not app_started:
        app_started = True
        update_clock()
        check_communication()
        threading.Thread(target=lire_uart_cnsp, daemon=True).start()

def logout():
    if recent_list is not None:
        recent_list.insert(0, f"SESSION {datetime.now().strftime('%H:%M:%S')} | Déconnexion | {CURRENT_USER}")
    root.withdraw()
    show_login()

def show_login():
    login = tk.Toplevel(root)
    login.title("CNS Supervision Prototype - Connexion")
    login.geometry("460x500")
    login.configure(bg=BG)
    login.resizable(False, False)
    login.minsize(460, 500)
    login.grab_set()
    login.update_idletasks()
    x = (login.winfo_screenwidth() // 2) - 230
    y = (login.winfo_screenheight() // 2) - 250
    login.geometry(f"460x500+{x}+{y}")
    if LOGO_LOGIN is not None:
        tk.Label(login, image=LOGO_LOGIN, bg=BG).pack(pady=(18, 6))
    else:
        tk.Label(login, text="CNS PROTOTYPE", fg="white", bg=BG, font=("Arial", 26, "bold")).pack(pady=(28, 4))

    tk.Label(login, text="Plateforme de supervision CNS", fg=MUTED, bg=BG, font=("Arial", 12, "bold")).pack(pady=(0, 14))
    form = tk.Frame(login, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
    form.pack(padx=35, fill="x")
    tk.Label(form, text="Utilisateur", fg=MUTED, bg=PANEL, font=("Arial", 10, "bold")).pack(anchor="w", padx=18, pady=(18, 3))
    entry_user = tk.Entry(form, font=("Arial", 12), bg="#020617", fg="white", insertbackground="white", relief="flat")
    entry_user.pack(fill="x", padx=18, ipady=7)
    entry_user.insert(0, AUTH_USER)
    tk.Label(form, text="Mot de passe", fg=MUTED, bg=PANEL, font=("Arial", 10, "bold")).pack(anchor="w", padx=18, pady=(14, 3))
    entry_pass = tk.Entry(form, font=("Arial", 12), bg="#020617", fg="white", insertbackground="white", relief="flat", show="*")
    entry_pass.pack(fill="x", padx=18, ipady=7)
    label_error = tk.Label(form, text="", fg="#ef4444", bg=PANEL, font=("Arial", 9, "bold"))
    label_error.pack(anchor="w", padx=18, pady=(8, 0))

    def verifier_login(event=None):
        user = entry_user.get().strip()
        password = entry_pass.get().strip()
        if user == AUTH_USER and password == AUTH_PASSWORD:
            login.grab_release()
            login.destroy()
            start_dashboard()
        else:
            label_error.config(text="Identifiants incorrects")
            entry_pass.delete(0, tk.END)
            entry_pass.focus_set()

    tk.Button(form, text="Se connecter", command=verifier_login, bg=BLUE, fg="white", activebackground="#1d4ed8", activeforeground="white", relief="flat", font=("Arial", 11, "bold"), pady=8).pack(fill="x", padx=18, pady=(10, 18))
    tk.Label(login, text=f"Compte de démonstration : {AUTH_USER} / {AUTH_PASSWORD}", fg="#64748b", bg=BG, font=("Arial", 9)).pack(pady=10)
    entry_pass.focus_set()
    login.bind("<Return>", verifier_login)
    login.protocol("WM_DELETE_WINDOW", root.destroy)

def show_splash():
    splash = tk.Toplevel(root)
    splash.title("Chargement")
    splash.geometry("520x360")
    splash.configure(bg=BG)
    splash.resizable(False, False)
    splash.overrideredirect(True)

    splash.update_idletasks()
    x = (splash.winfo_screenwidth() // 2) - 260
    y = (splash.winfo_screenheight() // 2) - 180
    splash.geometry(f"520x360+{x}+{y}")

    frame = tk.Frame(splash, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
    frame.pack(fill="both", expand=True, padx=18, pady=18)

    if LOGO_FULL is not None:
        tk.Label(frame, image=LOGO_FULL, bg=PANEL).pack(pady=(22, 8))
    else:
        tk.Label(frame, text="CNS PROTOTYPE", fg="white", bg=PANEL, font=("Arial", 28, "bold")).pack(pady=(30, 8))

    tk.Label(frame, text="Plateforme de supervision des systèmes CNS", fg="white", bg=PANEL, font=("Arial", 14, "bold")).pack()
    tk.Label(frame, text="Projet de stage · Données représentatives", fg=MUTED, bg=PANEL, font=("Arial", 10, "bold")).pack(pady=(6, 0))
    tk.Label(frame, text="Version 1.0", fg="#60a5fa", bg=PANEL, font=("Consolas", 10, "bold")).pack(pady=(8, 0))

    status = tk.Label(frame, text="Initialisation...", fg=MUTED, bg=PANEL, font=("Arial", 10, "bold"))
    status.pack(pady=(18, 4))

    progress = tk.Canvas(frame, width=340, height=16, bg="#020617", highlightthickness=0)
    progress.pack()

    def animate(step=0):
        progress.delete("all")
        progress.create_rectangle(0, 0, 340, 16, fill="#1e293b", outline="#1e293b")
        progress.create_rectangle(0, 0, int(340 * step / 100), 16, fill=BLUE, outline=BLUE)

        if step < 35:
            status.config(text="Initialisation de l'interface...")
        elif step < 70:
            status.config(text="Chargement du protocole CNSP...")
        else:
            status.config(text="Préparation de la connexion utilisateur...")

        if step >= 100:
            splash.destroy()
            show_login()
        else:
            splash.after(25, lambda: animate(step + 2))

    animate()


btn_logout.config(command=logout)
show_splash()
root.mainloop()
