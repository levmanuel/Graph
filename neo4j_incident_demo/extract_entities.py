"""
NER par règles — extraction d'entités depuis le TEXTE des incidents.

L'extracteur ne lit QUE le champ `description` (il ignore la vérité terrain)
afin de simuler une vraie tâche de reconnaissance d'entités nommées. Il combine :

  - un *gazetteer* (dictionnaire de noms connus issus de referentiel.py) pour
    les systèmes et les causes racines,
  - des motifs déclencheurs (« détecté par l'équipe X », « résolution assurée
    par l'équipe X », …) pour distinguer l'équipe de DÉTECTION de l'équipe de
    RÉSOLUTION,
  - des expressions régulières de dates/heures pour reconstruire la timeline
    (première occurrence = détection, dernière = résolution).

Le résultat est comparé à la vérité terrain pour afficher un taux de restitution
par champ — la preuve, pour la démo, que « le NER fonctionne ».

Sortie : data/entites.json  (uniquement les entités extraites du texte)

100 % offline, uniquement la bibliothèque standard.
"""

import os
import re
import json
from datetime import datetime

import referentiel as ref

ICI = os.path.dirname(os.path.abspath(__file__))
ENTREE = os.path.join(ICI, "data", "incidents.json")
SORTIE = os.path.join(ICI, "data", "entites.json")

# Alternation regex des noms connus (les plus longs d'abord pour éviter les
# recouvrements partiels).
def _alternation(noms):
    return "|".join(re.escape(n) for n in sorted(noms, key=len, reverse=True))

_TEAMS = _alternation(ref.liste_equipes())
_SYSTEMES = _alternation(ref.liste_systemes())
_ROOTS = _alternation(ref.liste_root_causes())

# --- Équipe de détection : motifs déclencheurs ------------------------------
# ([Ll]' → l'apostrophe peut être en début de phrase, donc L majuscule possible)
RE_DETECTION = [
    re.compile(r"[Ll]'équipe (" + _TEAMS + r") a détecté"),
    re.compile(r"détectée? par l'équipe (" + _TEAMS + r")"),
    re.compile(r"constatée? par l'équipe (" + _TEAMS + r")"),
    re.compile(r"[Ll]'équipe (" + _TEAMS + r") signale"),
]

# --- Équipe de résolution : motifs déclencheurs -----------------------------
RE_RESOLUTION = [
    re.compile(r"[Ll]'équipe (" + _TEAMS + r") est intervenue"),
    re.compile(r"[Rr]ésolution assurée par l'équipe (" + _TEAMS + r")"),
    re.compile(r"[Ll]'équipe (" + _TEAMS + r") clôture"),
    re.compile(r"[Ll]'équipe (" + _TEAMS + r") a (?:restauré|rétabli)"),
]

# --- Système impacté (souvent entre guillemets « ») -------------------------
RE_SYSTEME = re.compile(r"(" + _SYSTEMES + r")")

# --- Cause racine -----------------------------------------------------------
RE_ROOT = re.compile(r"(" + _ROOTS + r")")

# --- Dates / heures : YYYY-MM-DD [à] HHhMM ----------------------------------
RE_DATE_HEURE = re.compile(r"(\d{4}-\d{2}-\d{2})\s+(?:à\s+)?(\d{1,2})h(\d{2})")


def _premier_match(patterns, texte):
    for pat in patterns:
        m = pat.search(texte)
        if m:
            return m.group(1)
    return None


def extraire(texte: str) -> dict:
    """Extrait les entités d'un narratif d'incident (texte seul)."""
    equipe_det = _premier_match(RE_DETECTION, texte)
    equipe_res = _premier_match(RE_RESOLUTION, texte)

    m_sys = RE_SYSTEME.search(texte)
    systeme = m_sys.group(1) if m_sys else None

    m_root = RE_ROOT.search(texte)
    root_cause = m_root.group(1) if m_root else None

    # Timeline : toutes les occurrences date+heure, dans l'ordre du texte.
    horodatages = []
    for m in RE_DATE_HEURE.finditer(texte):
        jour, hh, mm = m.group(1), int(m.group(2)), int(m.group(3))
        dt = datetime.strptime(f"{jour} {hh:02d}:{mm:02d}", "%Y-%m-%d %H:%M")
        horodatages.append(dt)

    date_detection = date_resolution = None
    mttr_minutes = None
    if len(horodatages) >= 2:
        date_detection = min(horodatages[0], horodatages[-1])
        date_resolution = max(horodatages[0], horodatages[-1])
        mttr_minutes = int((date_resolution - date_detection).total_seconds() // 60)
    elif len(horodatages) == 1:
        date_detection = horodatages[0]

    root_cat = ref.ROOT_CAUSES.get(root_cause) if root_cause else None

    return {
        "systeme": systeme,
        "equipe_detection": equipe_det,
        "equipe_resolution": equipe_res,
        "root_cause": root_cause,
        "root_cause_categorie": root_cat,
        "date_detection": date_detection.isoformat(timespec="minutes") if date_detection else None,
        "date_resolution": date_resolution.isoformat(timespec="minutes") if date_resolution else None,
        "mttr_minutes": mttr_minutes,
    }


# Champs évalués contre la vérité terrain (la sévérité n'est pas ré-extraite en
# tant que telle ; elle est portée par le narratif et conservée au chargement).
CHAMPS_EVALUES = [
    "systeme", "equipe_detection", "equipe_resolution",
    "root_cause", "date_detection", "date_resolution", "mttr_minutes",
]


def main():
    with open(ENTREE, encoding="utf-8") as f:
        incidents = json.load(f)

    resultats = []
    compteurs = {c: 0 for c in CHAMPS_EVALUES}

    for inc in incidents:
        entites = extraire(inc["description"])
        gt = inc["ground_truth"]
        for c in CHAMPS_EVALUES:
            if entites.get(c) == gt.get(c):
                compteurs[c] += 1
        resultats.append({
            "id": inc["id"],
            "titre": inc["titre"],
            "severite": gt["severite"],          # portée par le texte, conservée
            "description": inc["description"],
            "entites": entites,
        })

    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with open(SORTIE, "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)

    n = len(incidents)
    print("=" * 70)
    print("EXTRACTION NER (RÈGLES + GAZETTEER)")
    print("=" * 70)
    print(f"{n} incidents traités → {SORTIE}")
    print("-" * 70)
    print("Taux de restitution vs vérité terrain :")
    for c in CHAMPS_EVALUES:
        taux = 100.0 * compteurs[c] / n
        print(f"  {c:22s} : {compteurs[c]:3d}/{n}  ({taux:5.1f} %)")
    global_ok = sum(compteurs.values())
    global_total = n * len(CHAMPS_EVALUES)
    print("-" * 70)
    print(f"  GLOBAL                 : {global_ok}/{global_total} "
          f"({100.0 * global_ok / global_total:5.1f} %)")
    print("-" * 70)
    ex = resultats[0]
    print("Exemple d'extraction :")
    print(f"  Texte  : {ex['description']}")
    print(f"  Entités: {json.dumps(ex['entites'], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
