import os
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib import animation
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("SIMULATION - ÉVOLUTION CHRONOLOGIQUE DU RÉSEAU DE PAIEMENTS")
print("=" * 70)

# ============================================================================
# DONNÉES SYNTHÉTIQUES
# ============================================================================
np.random.seed(42)
acteur_focus = "CLIENT_A"
transactions = []
date_start = datetime(2024, 1, 1)

# Phase 1 (jours 0-59) : 2 fournisseurs réguliers, comportement stable
for i in range(40):
    transactions.append({
        'date': date_start + timedelta(days=i * 1.5),
        'debtor': acteur_focus,
        'creditor': np.random.choice(['FOUR_1', 'FOUR_2']),
        'amount': max(100, np.random.normal(1000, 150)),
        'phase': 'Normal',
        'is_anomaly': False
    })

# Phase 2 (jours 60-89) : Nouveau fournisseur légitime
date_p2 = date_start + timedelta(days=60)
for i in range(15):
    f = np.random.choice(['FOUR_1', 'FOUR_2', 'FOUR_3'], p=[0.4, 0.4, 0.2])
    transactions.append({
        'date': date_p2 + timedelta(days=i * 2),
        'debtor': acteur_focus,
        'creditor': f,
        'amount': max(100, np.random.normal(1000, 150)),
        'phase': 'Expansion',
        'is_anomaly': (f == 'FOUR_3' and i == 0)
    })

# Phase 3 (jours 90-119) : Activité normale à 3 fournisseurs
date_p3 = date_start + timedelta(days=90)
for i in range(20):
    transactions.append({
        'date': date_p3 + timedelta(days=i * 1.5),
        'debtor': acteur_focus,
        'creditor': np.random.choice(['FOUR_1', 'FOUR_2', 'FOUR_3']),
        'amount': max(100, np.random.normal(1000, 150)),
        'phase': 'Stable',
        'is_anomaly': False
    })

# Phase 4 (jours 120-131) : BURST + tiers suspects
date_p4 = date_start + timedelta(days=120)
suspects = ['FOUR_X', 'FOUR_Y', 'FOUR_Z']
for i in range(24):
    f = np.random.choice(
        ['FOUR_1', 'FOUR_2', 'FOUR_3', 'FOUR_X', 'FOUR_Y', 'FOUR_Z'],
        p=[0.25, 0.15, 0.10, 0.20, 0.15, 0.15]
    )
    is_sus = f in suspects
    transactions.append({
        'date': date_p4 + timedelta(days=i * 0.5),
        'debtor': acteur_focus,
        'creditor': f,
        'amount': max(100, np.random.normal(5500 if is_sus else 1000, 400)),
        'phase': 'Suspect',
        'is_anomaly': is_sus
    })

# Phase 5 (jours 150-180) : Retour normal
date_p5 = date_start + timedelta(days=150)
for i in range(15):
    transactions.append({
        'date': date_p5 + timedelta(days=i * 2),
        'debtor': acteur_focus,
        'creditor': np.random.choice(['FOUR_1', 'FOUR_2', 'FOUR_3']),
        'amount': max(100, np.random.normal(1000, 150)),
        'phase': 'Retour normal',
        'is_anomaly': False
    })

df = pd.DataFrame(transactions).sort_values('date').reset_index(drop=True)
print(f"Transactions : {len(df)} | Anomalies : {df['is_anomaly'].sum()}")
print(f"Periode      : {df['date'].min().date()} -> {df['date'].max().date()}")

# ============================================================================
# POSITIONS FIXES
# ============================================================================
all_creditors = ['FOUR_1', 'FOUR_2', 'FOUR_3', 'FOUR_X', 'FOUR_Y', 'FOUR_Z']
labels_nice = {
    'FOUR_1': 'FOURN_1', 'FOUR_2': 'FOURN_2', 'FOUR_3': 'FOURN_3',
    'FOUR_X': 'FOURN_X', 'FOUR_Y': 'FOURN_Y', 'FOUR_Z': 'FOURN_Z',
    acteur_focus: acteur_focus
}

pos = {acteur_focus: (0, 0)}
angles = np.linspace(0, 2 * np.pi, len(all_creditors), endpoint=False)
for cred, angle in zip(all_creditors, angles):
    pos[cred] = (2.2 * np.cos(angle), 2.2 * np.sin(angle))

PHASE_COLORS = {
    'Normal': '#2196F3', 'Expansion': '#4CAF50', 'Stable': '#4CAF50',
    'Suspect': '#F44336', 'Retour normal': '#4CAF50'
}

# ============================================================================
# GÉNÉRATION DU GIF
# ============================================================================
def build_gif(df, output_path, fps=3):
    fig = plt.figure(figsize=(18, 9), facecolor='#0d1117')
    gs = gridspec.GridSpec(4, 2, left=0.02, right=0.98,
                           top=0.92, bottom=0.06, wspace=0.35, hspace=0.55)
    ax_net = fig.add_subplot(gs[:, 0])
    ax_txn = fig.add_subplot(gs[0, 1])
    ax_tier = fig.add_subplot(gs[1, 1])
    ax_amt  = fig.add_subplot(gs[2, 1])
    ax_ano  = fig.add_subplot(gs[3, 1])

    G = nx.DiGraph()
    G.add_node(acteur_focus)
    seen_creditors = set()
    hist = {'dates': [], 'n_txn': [], 'n_tier': [], 'amt': [], 'ano': []}

    def animate(frame):
        ax_net.clear()
        ax_txn.clear(); ax_tier.clear(); ax_amt.clear(); ax_ano.clear()

        for ax in [ax_net, ax_txn, ax_tier, ax_amt, ax_ano]:
            ax.set_facecolor('#161b22')
            for sp in ax.spines.values():
                sp.set_edgecolor('#30363d')

        row = df.iloc[frame]
        creditor = row['creditor']
        is_new = creditor not in seen_creditors
        seen_creditors.add(creditor)

        if not G.has_node(creditor):
            G.add_node(creditor)
        if G.has_edge(acteur_focus, creditor):
            G[acteur_focus][creditor]['weight'] += 1
            G[acteur_focus][creditor]['total'] += row['amount']
        else:
            G.add_edge(acteur_focus, creditor, weight=1, total=row['amount'])

        df_so_far = df.iloc[:frame + 1]
        hist['dates'].append(row['date'])
        hist['n_txn'].append(frame + 1)
        hist['n_tier'].append(df_so_far['creditor'].nunique())
        hist['amt'].append(df_so_far['amount'].sum() / 1000)
        hist['ano'].append(int(df_so_far['is_anomaly'].sum()))

        days_axis = [(d - hist['dates'][0]).days for d in hist['dates']]
        max_day = (df['date'].max() - df['date'].min()).days

        # ── RÉSEAU ──
        present_nodes = list(G.nodes())
        present_creds = [n for n in present_nodes if n != acteur_focus]
        pos_present = {k: v for k, v in pos.items() if k in present_nodes}

        if present_creds:
            colors_c, sizes_c = [], []
            for n in present_creds:
                if n in suspects:
                    colors_c.append('#F44336'); sizes_c.append(2200)
                elif n == creditor and is_new:
                    colors_c.append('#FF9800'); sizes_c.append(2200)
                else:
                    colors_c.append('#4CAF50'); sizes_c.append(1600)
            nx.draw_networkx_nodes(G, pos_present, nodelist=present_creds,
                                   node_color=colors_c, node_size=sizes_c,
                                   alpha=0.9, ax=ax_net)

        nx.draw_networkx_nodes(G, pos_present, nodelist=[acteur_focus],
                               node_color='#1565C0', node_size=3200,
                               alpha=1.0, ax=ax_net)

        for u, v, data in G.edges(data=True):
            w = data['weight']
            color = '#F44336' if v in suspects else \
                    ('#FF9800' if (v == creditor and is_new) else '#546E7A')
            nx.draw_networkx_edges(
                G, pos_present, [(u, v)],
                width=min(1 + w * 0.6, 7), alpha=0.85 if color != '#546E7A' else 0.5,
                edge_color=color, arrowsize=18, arrowstyle='->',
                ax=ax_net, connectionstyle='arc3,rad=0.08')

        nx.draw_networkx_labels(
            G, pos_present,
            labels={n: labels_nice.get(n, n) for n in present_nodes},
            font_size=8, font_weight='bold', font_color='white', ax=ax_net)

        edge_lbl = {(u, v): f"x{d['weight']}" for u, v, d in G.edges(data=True)}
        nx.draw_networkx_edge_labels(G, pos_present, edge_lbl,
                                     font_size=7, font_color='#90CAF9', ax=ax_net)

        phase_color = PHASE_COLORS.get(row['phase'], 'white')
        anomaly_tag = '  ANOMALIE !' if row['is_anomaly'] else ''
        ax_net.set_title(
            f"Reseau {acteur_focus}  |  {row['date'].strftime('%d %b %Y')}"
            f"  [{row['phase']}]{anomaly_tag}",
            fontsize=12, fontweight='bold', color=phase_color, pad=10)

        tag = 'NOUVEAU TIERS' if is_new else ('SUSPECT' if creditor in suspects else 'Connu')
        ax_net.text(0.01, 0.01,
                    f"-> {labels_nice.get(creditor, creditor)}   {row['amount']:.0f}EUR   {tag}",
                    transform=ax_net.transAxes, fontsize=9, color='white', va='bottom',
                    bbox=dict(facecolor='#1e2a3a', edgecolor='#30363d', boxstyle='round,pad=0.4'))

        ax_net.set_xlim(-3.2, 3.2); ax_net.set_ylim(-3.2, 3.2); ax_net.axis('off')

        patches = [mpatches.Patch(color='#1565C0', label='Client focus'),
                   mpatches.Patch(color='#4CAF50', label='Fournisseur connu'),
                   mpatches.Patch(color='#FF9800', label='Nouveau tiers'),
                   mpatches.Patch(color='#F44336', label='Tiers suspect')]
        ax_net.legend(handles=patches, loc='upper right', fontsize=8,
                      framealpha=0.6, facecolor='#161b22',
                      labelcolor='white', edgecolor='#30363d')

        # ── STATS ──
        def style(ax, title):
            ax.set_title(title, fontsize=9, color='#90CAF9', pad=4)
            ax.tick_params(colors='#8b949e', labelsize=7)
            ax.set_xlim(0, max_day)
            ax.grid(True, alpha=0.15, color='#30363d')
            if days_axis:
                ax.axvline(days_axis[-1], color='white', alpha=0.2,
                           linewidth=0.8, linestyle='--')

        ax_txn.fill_between(days_axis, hist['n_txn'], alpha=0.3, color='#2196F3')
        ax_txn.plot(days_axis, hist['n_txn'], color='#2196F3', linewidth=1.5)
        style(ax_txn, 'Transactions cumulees')

        ax_tier.fill_between(days_axis, hist['n_tier'], alpha=0.3, color='#4CAF50')
        ax_tier.step(days_axis, hist['n_tier'], color='#4CAF50', lw=1.5, where='post')
        style(ax_tier, 'Tiers distincts')

        ax_amt.fill_between(days_axis, hist['amt'], alpha=0.3, color='#FF9800')
        ax_amt.plot(days_axis, hist['amt'], color='#FF9800', linewidth=1.5)
        style(ax_amt, 'Montant cumule (kEUR)')

        ax_ano.fill_between(days_axis, hist['ano'], alpha=0.4, color='#F44336')
        ax_ano.plot(days_axis, hist['ano'], color='#F44336', lw=2, marker='x', ms=5)
        style(ax_ano, 'Anomalies cumulees')
        ax_ano.set_xlabel('Jours depuis J0', fontsize=8, color='#8b949e')

        fig.suptitle(
            f"Detection d'anomalies - Reseau de paiements  "
            f"({frame + 1}/{len(df)} transactions)",
            fontsize=13, color='#c9d1d9', fontweight='bold', y=0.97)

    anim = animation.FuncAnimation(fig, animate, frames=len(df),
                                   interval=1000 // fps, repeat=True)

    print(f"  Generation : {len(df)} frames a {fps} fps ...")
    anim.save(output_path, writer='pillow', fps=fps, dpi=90)
    plt.close()
    size_mb = os.path.getsize(output_path) / 1_000_000
    print(f"GIF sauvegarde : {output_path}  ({size_mb:.1f} MB)")


out = 'network_evolution_CLIENT_A.gif'
build_gif(df, out, fps=3)

print("""
Phases du GIF :
  J0-J59    : 2 fournisseurs, activite stable
  J60       : FOURN_3 apparait en orange (nouveau tiers legitime)
  J90-J119  : Activite normale a 3 fournisseurs
  J120-J131 : BURST + FOURN_X/Y/Z en rouge (suspects)
  J150+     : Retour a la normale
""")