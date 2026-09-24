START_BYTE = 0xAA
VERSION = 0x01
FRAME_SIZE = 7

SYSTEMES = {
    0x01: "DME",
    0x02: "ILS_LOCALIZER",
    0x03: "GLIDE_SLOPE",
    0x04: "VHF",
    0x05: "ADS_B",
    0x06: "ONDULEUR"
}

DEFAUTS = {
    0x00: "OK",
    0x01: "FONCTION_PERDUE",
    0x02: "SIGNAL_PERDU",
    0x03: "TEMPERATURE_ELEVEE",
    0x04: "ALIMENTATION_COUPEE",
    0x10: "SECTEUR_COUPE",
    0x11: "BATTERIE_FAIBLE",
    0x12: "ONDULEUR_HS",
    0x13: "ALIMENTATION_CNS"
}

ETATS = {
    0x00: "NORMAL",
    0x01: "WARNING",
    0x02: "ALARME",
    0x03: "HORS_SERVICE"
}

def calculer_checksum(trame_sans_checksum):
    return sum(trame_sans_checksum) & 0xFF

def verifier_checksum(trame):
    """Retourne True si le checksum de la trame CNSP est valide."""
    if len(trame) != FRAME_SIZE:
        return False
    return trame[-1] == calculer_checksum(trame[:-1])


def decoder_trame(trame):
    if len(trame) != FRAME_SIZE:
        return None

    start = trame[0]
    version = trame[1]
    adresse = trame[2]
    defaut = trame[3]
    etat = trame[4]
    compteur = trame[5]
    checksum = trame[6]

    if start != START_BYTE:
        return None

    if version != VERSION:
        return None

    if not verifier_checksum(trame):
        return None

    return {
        "version": version,
        "systeme": SYSTEMES.get(adresse, "INCONNU"),
        "defaut": DEFAUTS.get(defaut, "INCONNU"),
        "etat": ETATS.get(etat, "INCONNU"),
        "compteur": compteur
    }
