from database import lire_historique

historique = lire_historique()

print("===== HISTORIQUE DES EVENEMENTS =====\n")

for ligne in historique:
    date_heure, temps_ms, systeme, defaut, etat = ligne

    print(f"{date_heure} | {temps_ms} ms | {systeme} | {defaut} | {etat}")