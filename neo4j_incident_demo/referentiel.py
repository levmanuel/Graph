"""
Référentiel métier partagé — source de vérité unique de la démo.

Ce module centralise les vocabulaires contrôlés (équipes, systèmes, causes
racines) ainsi que les relations structurelles fixes de l'ontologie
(responsabilité d'une équipe sur un système, dépendances entre systèmes).

Il est importé par :
  - generate_incidents.py  → pour tirer des combinaisons cohérentes
  - extract_entities.py    → comme *gazetteer* (dictionnaire de reconnaissance NER)
  - load_neo4j.py          → pour créer les relations RESPONSABLE_DE / DEPEND_DE

Aucune dépendance externe : uniquement la bibliothèque standard.
"""

# ---------------------------------------------------------------------------
# ÉQUIPES  (nœud :Equipe)
# ---------------------------------------------------------------------------
# nom -> domaine
EQUIPES = {
    "Supervision Paiements": "Paiements",
    "Run Core Banking": "Core Banking",
    "Infrastructure & Réseau": "Infrastructure",
    "Sécurité Opérationnelle": "Sécurité",
    "Canaux Digitaux": "Canaux Digitaux",
    "Data & Réconciliation": "Data",
    "Monitoring 24/7 (NOC)": "Infrastructure",
}

# Équipes qui détectent typiquement les incidents (supervision / NOC / sécurité)
EQUIPES_DETECTION = [
    "Monitoring 24/7 (NOC)",
    "Sécurité Opérationnelle",
    "Supervision Paiements",
]

# ---------------------------------------------------------------------------
# SYSTÈMES / CONTEXTE OPÉRATIONNEL  (nœud :Systeme)
# ---------------------------------------------------------------------------
# nom -> { type, responsable }
#   type        : famille fonctionnelle (contexte opérationnel)
#   responsable : équipe propriétaire → relation (:Equipe)-[:RESPONSABLE_DE]->(:Systeme)
SYSTEMES = {
    "Virements SEPA":         {"type": "Paiements domestiques",     "responsable": "Supervision Paiements"},
    "Passerelle SWIFT":       {"type": "Paiements internationaux",  "responsable": "Supervision Paiements"},
    "Monétique Cartes":       {"type": "Cartes",                    "responsable": "Supervision Paiements"},
    "Core Banking":           {"type": "Core Banking",              "responsable": "Run Core Banking"},
    "Batch de Réconciliation":{"type": "Batch / Réconciliation",    "responsable": "Data & Réconciliation"},
    "Application Mobile":     {"type": "Mobile Banking",            "responsable": "Canaux Digitaux"},
    "Portail Web":            {"type": "Banque en ligne",           "responsable": "Canaux Digitaux"},
    "API Open Banking":       {"type": "API Ouverte (DSP2)",        "responsable": "Canaux Digitaux"},
}

# Dépendances techniques fixes → relation (:Systeme)-[:DEPEND_DE]->(:Systeme)
# Core Banking est le hub central : la plupart des systèmes en dépendent.
DEPENDANCES_SYSTEMES = [
    ("Application Mobile",      "API Open Banking"),
    ("Portail Web",            "API Open Banking"),
    ("API Open Banking",       "Core Banking"),
    ("Virements SEPA",         "Core Banking"),
    ("Monétique Cartes",       "Core Banking"),
    ("Passerelle SWIFT",       "Core Banking"),
    ("Batch de Réconciliation","Core Banking"),
]

# ---------------------------------------------------------------------------
# CAUSES RACINES  (nœud :RootCause)
# ---------------------------------------------------------------------------
# libelle -> categorie
ROOT_CAUSES = {
    "un déploiement défectueux":                    "Changement / Déploiement",
    "une erreur de configuration":                  "Changement / Déploiement",
    "l'expiration d'un certificat TLS":             "Changement / Déploiement",
    "une régression logicielle":                    "Bug logiciel",
    "une fuite mémoire":                            "Bug logiciel",
    "une saturation du réseau":                     "Réseau",
    "une panne matérielle serveur":                 "Matériel",
    "une erreur de manipulation":                   "Erreur humaine",
    "l'indisponibilité d'un prestataire externe":   "Dépendance externe",
    "un pic de charge imprévu":                     "Capacité / Charge",
}

# ---------------------------------------------------------------------------
# SÉVÉRITÉS  (propriété de :Incident)
# ---------------------------------------------------------------------------
SEVERITES = ["Critique", "Majeur", "Mineur"]


# ---------------------------------------------------------------------------
# Aides
# ---------------------------------------------------------------------------
def equipe_responsable(systeme: str) -> str:
    """Retourne l'équipe propriétaire d'un système."""
    return SYSTEMES[systeme]["responsable"]


def liste_systemes():
    return list(SYSTEMES.keys())


def liste_equipes():
    return list(EQUIPES.keys())


def liste_root_causes():
    return list(ROOT_CAUSES.keys())
