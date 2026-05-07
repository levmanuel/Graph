# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Graph-based anomaly detection system for payment networks. Two audiences: a from-scratch introduction to graph theory for non-technical readers (`introduction_graphes.ipynb`), and a standalone animated GIF generator (`generate_network_gif.py`).

## Commands

```bash
# Run the introductory notebook
jupyter notebook introduction_graphes.ipynb

# Validate the notebook executes without errors
papermill introduction_graphes.ipynb /tmp/intro_test.ipynb --kernel python3

# Generate animated GIF → outputs network_evolution_CLIENT_A.gif
python3 generate_network_gif.py

# Install dependencies
pip install numpy pandas networkx matplotlib seaborn scikit-learn pillow papermill
```

## Architecture

**Two entry points (no external data — everything is generated in-memory):**

- `introduction_graphes.ipynb` — 41 cells, 7 parts, beginner audience. Structure: markdown analogy cell → code cell → "À retenir" summary. No formulas anywhere.
- `generate_network_gif.py` — single script, 5 synthetic transaction phases (Normal → Expansion → Stable → Suspect → Retour normal), outputs a dark-theme animated GIF using `matplotlib.animation.FuncAnimation`.

**Notebook cell ID naming convention** (used by `NotebookEdit`):
```
title, setup, part1-intro, undirected-graph, directed-intro, directed-graph,
weighted-intro, weighted-graph, part1-summary, part2-intro, shortest-path,
connected-intro, connected-components, part2-summary, part3-intro,
degree-centrality, betweenness-intro, betweenness, pagerank-intro, pagerank,
centrality-summary, part4-intro, community-detection, community-fraud,
fraud-ring, part4-summary, part5-intro, embeddings, similarity-intro,
similarity-matrix, part5-summary, part6-intro, isolation-forest-visual,
if-score-viz, score-distribution, part6-summary, part7-intro, risk-signals,
investigation-workflow, case-study, final-summary
```

**Cross-cell state** — cells share variables set upstream:
- `G_paiements` (DiGraph), `clients`, `fournisseurs`, `pos`, `edge_labels`, `patch_c`, `patch_f` — created in `directed-graph`, reused in `weighted-graph`, `degree-centrality`, `embeddings`, `pagerank`
- `df_fiches` — created in `embeddings`, consumed in `similarity-matrix`
- `n_normal`, `X`, `scores`, `predictions` — created in `isolation-forest-visual`, consumed in `score-distribution`

**Shared data pipeline:**
1. Synthetic transactions in-memory (no files read/written)
2. NetworkX `DiGraph` — clients/suppliers as nodes, transactions as weighted directed edges
3. Per-node metrics: degree, betweenness, closeness, PageRank
4. `IsolationForest` on metric vectors for anomaly scoring
5. Matplotlib visualisations (static in notebook, animated GIF from script)

## Visualization Conventions

**Arrow visibility** — always use `min_source_margin` and `min_target_margin` (typically 20–25) when drawing directed edges, or arrowheads disappear behind large nodes:
```python
nx.draw_networkx_edges(G, pos, min_source_margin=22, min_target_margin=22, ...)
```

**Manual positions** — `spring_layout` produces unstable layouts for pedagogical graphs. Use `pos = {...}` dicts for any graph where spatial arrangement matters (community detection, fraud ring, PageRank).

**Curved arrows for directed graphs** — use `connectionstyle='arc3,rad=0.1'` (or 0.25 for same-pair bidirectional edges) so arrowheads on circular structures stay readable.

**Fraud ring pattern** — `FancyBboxPatch` with `facecolor='#FF6B6B', alpha=0.08` draws a shaded zone behind suspect nodes. Legend goes `bbox_to_anchor=(0.5, -0.03)` below the axes so it never hides nodes.

**Community detection** — `greedy_modularity_communities` returns communities in arbitrary order; the palette assignment `palette[i % len(palette)]` must be verified against the actual detected groupings after any graph change.

## Design Constraints (intro notebook)

- **No formulas** — mathematical notation is never shown; analogies do the work.
- **Analogy before code** — every concept is introduced in a markdown cell with a real-world parallel before the code cell.
- **Unique shortest path** — `nx.shortest_path` returns one path; the `G_nav` network is deliberately constructed so Alice→Bob→David (2 steps) is strictly shorter than Alice→Emma→Frank→David (3 steps).
- **PageRank coherence** — `G_pr` uses 5 sources → Gros Client → Fourn. A vs. 1 Petit Client → Fourn. B to produce a clear ~3× ratio (≈0.29 vs ≈0.10). Only 4 nodes are drawn (`G_draw`); the 5 source nodes are annotated as text.
