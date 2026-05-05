# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Graph-based anomaly detection system for payment networks. Two audiences: a from-scratch introduction to graph theory for non-technical readers, and a deeper technical walkthrough of the detection pipeline.

## Running the Code

```bash
# Introductory notebook (non-technical audience, starts from scratch)
jupyter notebook introduction_graphes.ipynb

# Technical deep-dive notebook (anomaly detection pipeline)
jupyter notebook tutorial_anomaly_detection.ipynb

# Generate animated GIF of network evolution
python3 generate_network_gif.py
```

## Dependencies

```bash
pip install numpy pandas networkx matplotlib seaborn scikit-learn pillow
```

## Architecture

**Three entry points:**

- `introduction_graphes.ipynb` — 7-part beginner notebook. Each concept is introduced with a real-world analogy before any code. Covers: graph types → navigation & connected components → centrality metrics → community detection → embeddings → Isolation Forest → fraud signal walkthrough. Designed for non-technical readers; no formulas shown.
- `tutorial_anomaly_detection.ipynb` — technical guide covering centrality metrics, embeddings, 6 risk factors (NOUVEAU_TIERS, CROSS_CLIENT_TIER, MONTANT_ATYPIQUE, OPERATION_RARE, ACTIVITE_ELEVEE, RESEAU_ATYPIQUE), and Isolation Forest scoring with a full investigation workflow.
- `generate_network_gif.py` — standalone script generating an animated GIF of payment network evolution across 5 synthetic phases (normal → expansion → anomalous → recovery → stabilization).

**Shared data pipeline (both notebooks):**
1. Synthetic transaction data generated in-memory — no external data sources
2. NetworkX `DiGraph` with clients/suppliers as nodes, transactions as weighted directed edges
3. Graph metrics per node: degree, betweenness, closeness, PageRank
4. Anomaly scoring via `IsolationForest` on metric vectors
5. Matplotlib visualizations (static in notebooks, animated GIF from script)

There are no tests, no build system, and no lint configuration — this is an exploratory/educational project.
