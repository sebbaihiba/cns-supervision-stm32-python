import sqlite3
from datetime import datetime

DB_NAME = "supervision.db"

def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historique (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_heure TEXT,
            temps_ms INTEGER,
            systeme TEXT,
            defaut TEXT,
            etat TEXT
        )
    """)

    conn.commit()
    conn.close()

def ajouter_evenement(temps_ms, systeme, defaut, etat):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    date_heure = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO historique (date_heure, temps_ms, systeme, defaut, etat)
        VALUES (?, ?, ?, ?, ?)
    """, (date_heure, temps_ms, systeme, defaut, etat))

    conn.commit()
    conn.close()

def lire_historique():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date_heure, temps_ms, systeme, defaut, etat
        FROM historique
        ORDER BY id DESC
        LIMIT 50
    """)

    lignes = cursor.fetchall()
    conn.close()

    return lignes