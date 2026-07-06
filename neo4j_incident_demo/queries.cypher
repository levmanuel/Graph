// ===========================================================================
// Requêtes de démonstration — graphe d'incidents opérationnels
// À copier-coller dans Neo4j Browser (http://localhost:7474).
// Exécuter les requêtes une par une.
// ===========================================================================

// 1) Vue d'ensemble : tout le graphe (limité pour rester lisible).
MATCH (n) RETURN n LIMIT 300;

// 2) Le référentiel structurel seul : équipes, systèmes, dépendances.
//    (met en évidence Core Banking comme hub central)
MATCH p=(:Systeme)-[:DEPEND_DE]->(:Systeme) RETURN p;
MATCH p=(:Equipe)-[:RESPONSABLE_DE]->(:Systeme) RETURN p;

// 3) Top des causes racines par nombre d'incidents.
MATCH (i:Incident)-[:CAUSE_PAR]->(r:RootCause)
RETURN r.libelle AS cause, r.categorie AS categorie, count(i) AS nb_incidents
ORDER BY nb_incidents DESC;

// 4) Systèmes les plus impactés + équipe responsable.
MATCH (i:Incident)-[:IMPACTE]->(s:Systeme)
OPTIONAL MATCH (e:Equipe)-[:RESPONSABLE_DE]->(s)
RETURN s.nom AS systeme, s.type AS type, e.nom AS equipe_responsable,
       count(i) AS nb_incidents
ORDER BY nb_incidents DESC;

// 5) MTTR moyen (minutes) par sévérité.
MATCH (i:Incident)
RETURN i.severite AS severite,
       count(i) AS nb,
       round(avg(i.mttr_minutes)) AS mttr_moyen_min
ORDER BY mttr_moyen_min DESC;

// 6) MTTR moyen par équipe de résolution.
MATCH (i:Incident)-[:RESOLU_PAR]->(e:Equipe)
RETURN e.nom AS equipe, count(i) AS nb_resolus,
       round(avg(i.mttr_minutes)) AS mttr_moyen_min
ORDER BY mttr_moyen_min DESC;

// 7) Chemin détection → incident → système impacté → équipe de résolution.
MATCH path=(det:Equipe)<-[:DETECTE_PAR]-(i:Incident)-[:IMPACTE]->(s:Systeme)
MATCH (i)-[:RESOLU_PAR]->(res:Equipe)
RETURN path LIMIT 25;

// 8) Incidents critiques les plus longs à résoudre (timeline).
MATCH (i:Incident {severite:'Critique'})
RETURN i.id AS incident, i.titre AS titre,
       i.date_detection AS detection, i.date_resolution AS resolution,
       i.mttr_minutes AS mttr_min
ORDER BY i.mttr_minutes DESC
LIMIT 10;

// 9) Corrélation cause racine ↔ système : quelles causes touchent quels systèmes.
MATCH (r:RootCause)<-[:CAUSE_PAR]-(i:Incident)-[:IMPACTE]->(s:Systeme)
RETURN r.libelle AS cause, s.nom AS systeme, count(i) AS nb
ORDER BY nb DESC
LIMIT 20;

// 10) « Blast radius » : incidents sur un système et ce dont ce système dépend.
MATCH (i:Incident)-[:IMPACTE]->(s:Systeme)-[:DEPEND_DE*0..2]->(dep:Systeme)
WHERE s.nom = 'Application Mobile'
RETURN i, s, dep;
