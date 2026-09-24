from database import init_database, lire_historique

init_database()
historique = lire_historique()

print("===== HISTORIQUE DES EVENEMENTS =====\n")

for ligne in historique:
    date_heure, compteur, systeme, defaut, etat = ligne
    print(f"{date_heure} | compteur={compteur} | {systeme} | {defaut} | {etat}")
