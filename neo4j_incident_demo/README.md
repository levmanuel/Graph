# Démo Neo4j — Graphe d'incidents opérationnels (contexte bancaire)

De **100 descriptions textuelles d'incidents** vers un **graphe explorable dans
Neo4j**, en passant par de la **reconnaissance d'entités (NER)**.

Le fil rouge : dans une banque, chaque incident opérationnel est raconté en
langage naturel (« Le 2025-10-14 à 00h24, l'équipe … a détecté … »). Isolés, ces
récits ne se recoupent pas. Transformés en graphe, ils révèlent des motifs :
quels systèmes tombent le plus, quelles causes racines reviennent, quelles
équipes détectent vs résolvent, où sont les dépendances critiques.

## Pipeline

```
generate_incidents.py     extract_entities.py          load_neo4j.py
   (templates FR)   ─────▶   (NER par règles)   ─────▶   (Bolt + dump Cypher)
        │                          │                          │
   data/incidents.json      data/entites.json           Neo4j (web + graphe)
   texte + vérité terrain   entités extraites du texte   http://localhost:7474
```

1. **Génération** — 100 incidents synthétiques, déterministes (seed fixe), rendus
   en narratifs français variés. On conserve la *vérité terrain* à côté du texte.
2. **NER** — l'extracteur ne lit **que le texte** et retrouve les équipes, la
   timeline (détection/résolution), le système impacté et la cause racine. Il
   affiche un **taux de restitution** face à la vérité terrain (preuve que ça marche).
3. **Chargement** — les entités deviennent des nœuds et relations Neo4j selon
   [l'ontologie simplifiée](./ontologie.md).

> **100 % offline et déterministe.** Les étapes 1 et 2 n'utilisent **aucune
> dépendance** (bibliothèque standard Python uniquement). Seuls le chargement
> direct et le notebook requièrent des paquets (voir `requirements.txt`).

## Démarrage rapide

```bash
# 1. (optionnel) dépendances pour chargement direct + notebook
pip install -r requirements.txt

# 2. Générer les incidents puis extraire les entités
python3 generate_incidents.py     # → data/incidents.json
python3 extract_entities.py       # → data/entites.json  (+ taux de restitution)

# 3. Démarrer Neo4j (interface web + Bolt)
docker compose up -d
#   interface web : http://localhost:7474   (login : neo4j / demopassword)

# 4. Charger le graphe
python3 load_neo4j.py             # via Bolt + écrit aussi incidents.cypher
```

Puis ouvrez **http://localhost:7474**, connectez-vous (`neo4j` / `demopassword`)
et exécutez les requêtes de [`queries.cypher`](./queries.cypher).

### Sans le driver Python

Si vous ne voulez pas installer `neo4j`, générez le dump statique et importez-le
à la main dans Neo4j Browser :

```bash
python3 load_neo4j.py --cypher-only   # → incidents.cypher
```

Copiez-collez le contenu de `incidents.cypher` dans Neo4j Browser (par blocs).

## L'ontologie en un coup d'œil

```
(:Incident)-[:DETECTE_PAR]->(:Equipe)      (:Incident)-[:CAUSE_PAR]->(:RootCause)
(:Incident)-[:RESOLU_PAR]->(:Equipe)       (:Incident)-[:IMPACTE]->(:Systeme)
(:Equipe)-[:RESPONSABLE_DE]->(:Systeme)    (:Systeme)-[:DEPEND_DE]->(:Systeme)
```

Détail complet, propriétés et correspondance NER → graphe : [`ontologie.md`](./ontologie.md).

## Contenu du dossier

| Fichier | Rôle |
|---------|------|
| `referentiel.py` | Vocabulaires contrôlés (équipes, systèmes, causes) + relations fixes. Source de vérité partagée. |
| `generate_incidents.py` | Génère les 100 narratifs + vérité terrain. |
| `extract_entities.py` | NER par règles/gazetteer + évaluation. |
| `load_neo4j.py` | Chargement Bolt + dump `incidents.cypher`. |
| `queries.cypher` | Requêtes de démo pour Neo4j Browser. |
| `docker-compose.yml` | Instance Neo4j (web `:7474` + Bolt `:7687`). |
| `ontologie.md` | Description détaillée de l'ontologie. |
| `demo_incidents_neo4j.ipynb` | Notebook pédagogique de bout en bout. |
| `requirements.txt` | Dépendances (chargement + notebook uniquement). |

## Notebook pédagogique

`demo_incidents_neo4j.ipynb` raconte la démo pas à pas — ontologie, exemples de
narratifs, extraction NER avant/après, visualisation du graphe avec `networkx`
(sans Neo4j en marche) et requêtes Cypher à exécuter dans Browser.

```bash
jupyter notebook demo_incidents_neo4j.ipynb
```

## Adapter la démo

Tout part de `referentiel.py` : ajoutez une équipe, un système ou une cause
racine, relancez `generate_incidents.py` puis `extract_entities.py`, et le NER
comme le graphe suivent automatiquement (le gazetteer se reconstruit depuis le
référentiel).
