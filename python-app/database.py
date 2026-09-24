import sqlite3
from datetime import datetime

DB_NAME = "supervision.db"


def init_database():
    """Initialise la base et migre l'ancien champ temps_ms vers compteur si besoin."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historique (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_heure TEXT,
            compteur INTEGER,
            systeme TEXT,
            defaut TEXT,
            etat TEXT
        )
    """)

    # Compatibilité avec une ancienne version de la base où le compteur
    # était nommé à tort "temps_ms".
    cursor.execute("PRAGMA table_info(historique)")
    colonnes = {ligne[1] for ligne in cursor.fetchall()}
    if "temps_ms" in colonnes and "compteur" not in colonnes:
        cursor.execute("ALTER TABLE historique RENAME COLUMN temps_ms TO compteur")

    conn.commit()
    conn.close()


def ajouter_evenement(compteur, systeme, defaut, etat):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    date_heure = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO historique (date_heure, compteur, systeme, defaut, etat)
        VALUES (?, ?, ?, ?, ?)
    """, (date_heure, compteur, systeme, defaut, etat))

    conn.commit()
    conn.close()


def lire_historique():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date_heure, compteur, systeme, defaut, etat
        FROM historique
        ORDER BY id DESC
        LIMIT 50
    """)

    lignes = cursor.fetchall()
    conn.close()

    return lignes
