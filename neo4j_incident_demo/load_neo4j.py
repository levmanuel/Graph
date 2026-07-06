"""
Chargement du graphe d'incidents dans Neo4j (+ génération d'un dump Cypher).

Lit `data/entites.json` (produit par extract_entities.py) et construit le graphe
selon l'ontologie simplifiée :

  (:Incident)-[:DETECTE_PAR]->(:Equipe)
  (:Incident)-[:RESOLU_PAR]->(:Equipe)
  (:Incident)-[:CAUSE_PAR]->(:RootCause)
  (:Incident)-[:IMPACTE]->(:Systeme)
  (:Equipe)-[:RESPONSABLE_DE]->(:Systeme)   (depuis referentiel.py)
  (:Systeme)-[:DEPEND_DE]->(:Systeme)       (depuis referentiel.py)

Deux modes :
  1. Écrit TOUJOURS un dump statique `incidents.cypher` (importable à la main
     dans Neo4j Browser, sans aucune dépendance).
  2. Si le driver `neo4j` est installé et qu'une instance est joignable, charge
     directement via Bolt. Passer --cypher-only pour ne produire que le dump.

Config via variables d'environnement (valeurs par défaut = docker-compose.yml) :
  NEO4J_URI       (défaut bolt://localhost:7687)
  NEO4J_USER      (défaut neo4j)
  NEO4J_PASSWORD  (défaut demopassword)
"""

import os
import sys
import json

import referentiel as ref

ICI = os.path.dirname(os.path.abspath(__file__))
ENTREE = os.path.join(ICI, "data", "entites.json")
DUMP = os.path.join(ICI, "incidents.cypher")

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
USER = os.environ.get("NEO4J_USER", "neo4j")
PASSWORD = os.environ.get("NEO4J_PASSWORD", "demopassword")

CONTRAINTES = [
    "CREATE CONSTRAINT incident_id IF NOT EXISTS FOR (i:Incident) REQUIRE i.id IS UNIQUE",
    "CREATE CONSTRAINT equipe_nom IF NOT EXISTS FOR (e:Equipe) REQUIRE e.nom IS UNIQUE",
    "CREATE CONSTRAINT systeme_nom IF NOT EXISTS FOR (s:Systeme) REQUIRE s.nom IS UNIQUE",
    "CREATE CONSTRAINT rootcause_lib IF NOT EXISTS FOR (r:RootCause) REQUIRE r.libelle IS UNIQUE",
]


def _q(valeur):
    """Échappe une valeur pour l'insérer dans une chaîne Cypher entre apostrophes."""
    if valeur is None:
        return "null"
    return "'" + str(valeur).replace("\\", "\\\\").replace("'", "\\'") + "'"


def charger_incidents():
    with open(ENTREE, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Référentiel structurel (équipes, systèmes, dépendances, responsabilités)
# ---------------------------------------------------------------------------
def cypher_referentiel():
    lignes = ["// --- Référentiel : équipes, systèmes, dépendances ---"]
    for nom, domaine in ref.EQUIPES.items():
        lignes.append(
            f"MERGE (e:Equipe {{nom:{_q(nom)}}}) SET e.domaine={_q(domaine)};")
    for nom, meta in ref.SYSTEMES.items():
        lignes.append(
            f"MERGE (s:Systeme {{nom:{_q(nom)}}}) SET s.type={_q(meta['type'])};")
    for lib, cat in ref.ROOT_CAUSES.items():
        lignes.append(
            f"MERGE (r:RootCause {{libelle:{_q(lib)}}}) SET r.categorie={_q(cat)};")
    # Responsabilité équipe -> système
    for nom, meta in ref.SYSTEMES.items():
        lignes.append(
            f"MATCH (e:Equipe {{nom:{_q(meta['responsable'])}}}), "
            f"(s:Systeme {{nom:{_q(nom)}}}) MERGE (e)-[:RESPONSABLE_DE]->(s);")
    # Dépendances système -> système
    for source, cible in ref.DEPENDANCES_SYSTEMES:
        lignes.append(
            f"MATCH (a:Systeme {{nom:{_q(source)}}}), (b:Systeme {{nom:{_q(cible)}}}) "
            f"MERGE (a)-[:DEPEND_DE]->(b);")
    return lignes


# ---------------------------------------------------------------------------
# 2. Incidents + relations extraites par le NER
# ---------------------------------------------------------------------------
def cypher_incidents(incidents):
    lignes = ["// --- Incidents et relations extraites (NER) ---"]
    for inc in incidents:
        e = inc["entites"]
        det = f"datetime({_q(e['date_detection'])})" if e["date_detection"] else "null"
        res = f"datetime({_q(e['date_resolution'])})" if e["date_resolution"] else "null"
        props = (
            f"id:{_q(inc['id'])}, titre:{_q(inc['titre'])}, "
            f"severite:{_q(inc['severite'])}, "
            f"date_detection: {det}, "
            f"date_resolution: {res}, "
            f"mttr_minutes: {e['mttr_minutes'] if e['mttr_minutes'] is not None else 'null'}, "
            f"description:{_q(inc['description'])}"
        )
        lignes.append(f"MERGE (i:Incident {{id:{_q(inc['id'])}}}) SET i += {{{props}}};")
        if e.get("systeme"):
            lignes.append(
                f"MATCH (i:Incident {{id:{_q(inc['id'])}}}), "
                f"(s:Systeme {{nom:{_q(e['systeme'])}}}) MERGE (i)-[:IMPACTE]->(s);")
        if e.get("root_cause"):
            lignes.append(
                f"MATCH (i:Incident {{id:{_q(inc['id'])}}}), "
                f"(r:RootCause {{libelle:{_q(e['root_cause'])}}}) "
                f"MERGE (i)-[:CAUSE_PAR]->(r);")
        if e.get("equipe_detection"):
            lignes.append(
                f"MATCH (i:Incident {{id:{_q(inc['id'])}}}), "
                f"(e:Equipe {{nom:{_q(e['equipe_detection'])}}}) "
                f"MERGE (i)-[:DETECTE_PAR]->(e);")
        if e.get("equipe_resolution"):
            lignes.append(
                f"MATCH (i:Incident {{id:{_q(inc['id'])}}}), "
                f"(e:Equipe {{nom:{_q(e['equipe_resolution'])}}}) "
                f"MERGE (i)-[:RESOLU_PAR]->(e);")
    return lignes


def ecrire_dump(incidents):
    lignes = ["// Dump Cypher — démo Neo4j graphe d'incidents",
              "// À exécuter dans Neo4j Browser (:play) ou via cypher-shell.",
              ""]
    lignes += CONTRAINTES_SEP()
    lignes.append("")
    lignes += cypher_referentiel()
    lignes.append("")
    lignes += cypher_incidents(incidents)
    with open(DUMP, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    print(f"Dump Cypher écrit → {DUMP} ({len(lignes)} lignes)")


def CONTRAINTES_SEP():
    return ["// --- Contraintes d'unicité ---"] + [c + ";" for c in CONTRAINTES]


# ---------------------------------------------------------------------------
# Chargement direct via le driver Bolt
# ---------------------------------------------------------------------------
def charger_bolt(incidents):
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("Driver 'neo4j' non installé → dump Cypher uniquement.")
        print("  (pip install neo4j  pour activer le chargement direct)")
        return False

    try:
        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
        driver.verify_connectivity()
    except Exception as exc:  # noqa: BLE001
        print(f"Neo4j injoignable sur {URI} ({exc}). Dump Cypher uniquement.")
        print("  Démarrez la base : docker compose up -d")
        return False

    with driver.session() as session:
        for c in CONTRAINTES:
            session.run(c)
        # Référentiel
        for nom, domaine in ref.EQUIPES.items():
            session.run("MERGE (e:Equipe {nom:$nom}) SET e.domaine=$d", nom=nom, d=domaine)
        for nom, meta in ref.SYSTEMES.items():
            session.run("MERGE (s:Systeme {nom:$nom}) SET s.type=$t", nom=nom, t=meta["type"])
        for lib, cat in ref.ROOT_CAUSES.items():
            session.run("MERGE (r:RootCause {libelle:$l}) SET r.categorie=$c", l=lib, c=cat)
        for nom, meta in ref.SYSTEMES.items():
            session.run(
                "MATCH (e:Equipe {nom:$e}),(s:Systeme {nom:$s}) MERGE (e)-[:RESPONSABLE_DE]->(s)",
                e=meta["responsable"], s=nom)
        for source, cible in ref.DEPENDANCES_SYSTEMES:
            session.run(
                "MATCH (a:Systeme {nom:$a}),(b:Systeme {nom:$b}) MERGE (a)-[:DEPEND_DE]->(b)",
                a=source, b=cible)
        # Incidents
        for inc in incidents:
            e = inc["entites"]
            session.run(
                """
                MERGE (i:Incident {id:$id})
                SET i.titre=$titre, i.severite=$sev, i.description=$desc,
                    i.date_detection = CASE WHEN $det IS NULL THEN null ELSE datetime($det) END,
                    i.date_resolution = CASE WHEN $res IS NULL THEN null ELSE datetime($res) END,
                    i.mttr_minutes=$mttr
                """,
                id=inc["id"], titre=inc["titre"], sev=inc["severite"],
                desc=inc["description"], det=e["date_detection"],
                res=e["date_resolution"], mttr=e["mttr_minutes"])
            if e.get("systeme"):
                session.run(
                    "MATCH (i:Incident {id:$id}),(s:Systeme {nom:$s}) MERGE (i)-[:IMPACTE]->(s)",
                    id=inc["id"], s=e["systeme"])
            if e.get("root_cause"):
                session.run(
                    "MATCH (i:Incident {id:$id}),(r:RootCause {libelle:$r}) MERGE (i)-[:CAUSE_PAR]->(r)",
                    id=inc["id"], r=e["root_cause"])
            if e.get("equipe_detection"):
                session.run(
                    "MATCH (i:Incident {id:$id}),(e:Equipe {nom:$e}) MERGE (i)-[:DETECTE_PAR]->(e)",
                    id=inc["id"], e=e["equipe_detection"])
            if e.get("equipe_resolution"):
                session.run(
                    "MATCH (i:Incident {id:$id}),(e:Equipe {nom:$e}) MERGE (i)-[:RESOLU_PAR]->(e)",
                    id=inc["id"], e=e["equipe_resolution"])

        compte = session.run("MATCH (i:Incident) RETURN count(i) AS n").single()["n"]
    driver.close()
    print(f"Chargement Bolt réussi sur {URI} — {compte} incidents dans le graphe.")
    return True


def main():
    cypher_only = "--cypher-only" in sys.argv
    incidents = charger_incidents()

    print("=" * 70)
    print("CHARGEMENT DU GRAPHE D'INCIDENTS DANS NEO4J")
    print("=" * 70)

    ecrire_dump(incidents)

    if cypher_only:
        print("Mode --cypher-only : chargement direct ignoré.")
        return

    print("-" * 70)
    charger_bolt(incidents)


if __name__ == "__main__":
    main()
