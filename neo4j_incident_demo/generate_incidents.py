"""
Génération de 100 descriptions d'incidents opérationnels bancaires (synthétique).

100 % offline et déterministe (seed fixe) — aucune dépendance externe, uniquement
la bibliothèque standard, dans l'esprit de `generate_network_gif.py`.

Pour chaque incident on tire une combinaison cohérente
(système, équipe de détection, équipe de résolution, cause racine, sévérité,
timeline détection < résolution), puis on la *rend* sous forme d'un narratif
français en langage naturel via plusieurs gabarits de phrases.

On conserve à la fois :
  - le texte (`description`)  → ce que « verra » le NER,
  - la vérité terrain (`ground_truth`) → pour évaluer l'extraction ensuite.

Sortie : data/incidents.json
"""

import os
import json
import random
from datetime import datetime, timedelta

import referentiel as ref

SEED = 42
NB_INCIDENTS = 100
DATE_DEBUT = datetime(2025, 1, 1, 0, 0)
DATE_FIN = datetime(2025, 12, 31, 23, 59)

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "data", "incidents.json")

# Fourchettes de durée de résolution (minutes) selon la sévérité.
DUREE_PAR_SEVERITE = {
    "Critique": (30, 240),
    "Majeur":   (60, 600),
    "Mineur":   (120, 1440),
}

# Pondération des sévérités : les incidents mineurs sont les plus fréquents.
POIDS_SEVERITE = [("Critique", 0.2), ("Majeur", 0.4), ("Mineur", 0.4)]

# Adjectif de sévérité pour fluidifier certains gabarits.
SEVERITE_ADJ = {"Critique": "critique", "Majeur": "majeur", "Mineur": "mineur"}

# Gabarits de narratif. Chaque gabarit contient VERBATIM les chaînes d'entités
# (équipes, système, cause racine, dates) afin que le NER puisse les retrouver.
GABARITS = [
    ("Le {date_det} à {heure_det}, l'équipe {equipe_det} a détecté un incident "
     "{sev_adj} sur le système « {systeme} ». L'analyse a révélé comme cause "
     "racine {root_cause}. L'équipe {equipe_res} est intervenue et a rétabli le "
     "service le {date_res} à {heure_res}."),

    ("Incident {severite} : le service « {systeme} » a présenté une dégradation, "
     "détectée par l'équipe {equipe_det} le {date_det} à {heure_det}. Origine du "
     "problème : {root_cause}. Résolution assurée par l'équipe {equipe_res} le "
     "{date_res} à {heure_res}."),

    ("{date_det} {heure_det} — l'équipe {equipe_det} signale une anomalie "
     "{sev_adj} sur « {systeme} ». Diagnostic : la cause racine est {root_cause}. "
     "Le {date_res} à {heure_res}, l'équipe {equipe_res} clôture l'incident après "
     "remise en service."),

    ("Une interruption {sev_adj} du système « {systeme} » a été constatée par "
     "l'équipe {equipe_det} le {date_det} à {heure_det}. Après investigation, la "
     "cause racine retenue est {root_cause}. L'équipe {equipe_res} a restauré le "
     "service le {date_res} à {heure_res}."),
]

TITRES = [
    "Interruption {systeme}",
    "Dégradation {systeme}",
    "Anomalie {systeme}",
    "Incident {systeme}",
]


def _tirage_pondere(rng, choix_poids):
    r = rng.random()
    cumul = 0.0
    for valeur, poids in choix_poids:
        cumul += poids
        if r <= cumul:
            return valeur
    return choix_poids[-1][0]


def _fmt_date(dt):
    return dt.strftime("%Y-%m-%d")


def _fmt_heure(dt):
    return dt.strftime("%Hh%M")


def generer_incidents(nb=NB_INCIDENTS, seed=SEED):
    """Retourne une liste de dicts {id, titre, description, ground_truth}."""
    rng = random.Random(seed)
    span = int((DATE_FIN - DATE_DEBUT).total_seconds())
    incidents = []

    for i in range(nb):
        systeme = rng.choice(ref.liste_systemes())
        severite = _tirage_pondere(rng, POIDS_SEVERITE)

        # Détection : NOC / sécurité / supervision, majoritairement.
        equipe_det = rng.choice(ref.EQUIPES_DETECTION)
        # Résolution : l'équipe propriétaire du système (parfois l'infra).
        if rng.random() < 0.75:
            equipe_res = ref.equipe_responsable(systeme)
        else:
            equipe_res = "Infrastructure & Réseau"

        root_cause = rng.choice(ref.liste_root_causes())

        # Timeline : détection aléatoire dans l'année, résolution après.
        date_detection = DATE_DEBUT + timedelta(seconds=rng.randint(0, span))
        dmin, dmax = DUREE_PAR_SEVERITE[severite]
        duree = rng.randint(dmin, dmax)
        date_resolution = date_detection + timedelta(minutes=duree)

        gabarit = rng.choice(GABARITS)
        description = gabarit.format(
            date_det=_fmt_date(date_detection),
            heure_det=_fmt_heure(date_detection),
            date_res=_fmt_date(date_resolution),
            heure_res=_fmt_heure(date_resolution),
            equipe_det=equipe_det,
            equipe_res=equipe_res,
            systeme=systeme,
            root_cause=root_cause,
            severite=severite,
            sev_adj=SEVERITE_ADJ[severite],
        )

        titre = rng.choice(TITRES).format(systeme=systeme)

        incidents.append({
            "id": f"INC-{i + 1:04d}",
            "titre": titre,
            "description": description,
            "ground_truth": {
                "systeme": systeme,
                "equipe_detection": equipe_det,
                "equipe_resolution": equipe_res,
                "root_cause": root_cause,
                "root_cause_categorie": ref.ROOT_CAUSES[root_cause],
                "severite": severite,
                "date_detection": date_detection.isoformat(timespec="minutes"),
                "date_resolution": date_resolution.isoformat(timespec="minutes"),
                "mttr_minutes": duree,
            },
        })

    return incidents


def main():
    incidents = generer_incidents()
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(incidents, f, ensure_ascii=False, indent=2)

    print("=" * 70)
    print("GÉNÉRATION DES INCIDENTS OPÉRATIONNELS (SYNTHÉTIQUE)")
    print("=" * 70)
    print(f"{len(incidents)} incidents générés → {SORTIE}")
    print("-" * 70)
    print("Exemple de narratif :")
    print(f"  [{incidents[0]['id']}] {incidents[0]['description']}")
    print("-" * 70)
    # Contrôle de cohérence : détection < résolution pour tous.
    ok = all(
        inc["ground_truth"]["date_detection"] < inc["ground_truth"]["date_resolution"]
        for inc in incidents
    )
    print(f"Timeline cohérente (détection < résolution) sur les {len(incidents)} "
          f"incidents : {'OK' if ok else 'ÉCHEC'}")


if __name__ == "__main__":
    main()
