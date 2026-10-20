#!/usr/bin/env python3
"""fig4: KNIME-Workflow als Artikel-Grafik (300 dpi PNG).
Stilisiert wie ein KNIME-Editor-Screenshot: graue Knoten mit Dreieck-
ports (in gelb, out rot/blau), nummerierte State-Annotationen,
Metanode-Rahmen, Beschriftung der Referenz-Kennzahlen."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, FancyBboxPatch
from matplotlib.lines import Line2D

NODE_W, NODE_H = 2.05, 0.5
COL = dict(reader='#d9d9d9', filter='#d9d9d9', manip='#cfe2f3',
           learner='#d5e8d4', script='#ffe6cc', vis='#dae8fc', sink='#e1d5e7')


def node(ax, x, y, label, kind, num=None):
    ax.add_patch(Rectangle((x, y), NODE_W, NODE_H, fc=COL[kind],
                           ec='#666', lw=0.8, zorder=2))
    ax.text(x + NODE_W / 2, y + NODE_H / 2, label, fontsize=6.3,
            ha='center', va='center', zorder=3)
    # ports: in (gelbes Dreieck links), out (rotes Dreieck rechts)
    ax.add_patch(Polygon([[x - 0.09, y + 0.16], [x - 0.02, y + 0.25],
                          [x - 0.02, y + 0.07]], fc='#ffd966', ec='#333',
                         lw=0.4, zorder=3))
    ax.add_patch(Polygon([[x + NODE_W + 0.09, y + 0.16],
                          [x + NODE_W + 0.02, y + 0.25],
                          [x + NODE_W + 0.02, y + 0.07]],
                         fc='#f44336', ec='#333', lw=0.4, zorder=3))
    if num is not None:
        ax.text(x - 0.13, y + 0.02, str(num), fontsize=5.5, color='#555')


def conn(ax, x1, y1, x2, y2, style='-'):
    ax.add_line(Line2D([x1, x2], [y1, y2], color='#333', lw=0.9,
                       zorder=1, linestyle=style))


fig, ax = plt.subplots(figsize=(11, 6.2), dpi=300)
ax.set_xlim(0, 22); ax.set_ylim(0, 12.4); ax.axis('off')
ax.text(11, 12.0, 'KNIME Reference Workflow: Tomato Brix Fusion Analysis with Correction Variants (NIR-IP external reference, Section 2.1/6.7)',
        fontsize=9.5, fontweight='bold', ha='center')
ax.text(11, 11.55, 'Sources: A = T4-T5 (2,014 cleaned rows) · B = CSV export (1,506 rows) · seed 42 · reference scores: A 0.621 / B 0.722 / Fusion V0 0.545 / SNV 0.646',
        fontsize=6.4, color='#555', ha='center')

# --- Quelle A Reihe (oben) ---
yA = 10.0
node(ax, 0.5, yA, 'CSV Reader (A)\nT4-T5', 'reader', 1)
node(ax, 3.1, yA, 'Rule-based Row Filter\nADC ≥ 2³¹ OR ≤ 0', 'filter', 2)
node(ax, 5.7, yA, 'Normalizer\nV0 z-score / V1 SNV\nV2/V3 MSC', 'manip', 3)
conn(ax, 2.55, yA + 0.25, 3.1, yA + 0.25)
conn(ax, 5.15, yA + 0.25, 5.7, yA + 0.25)

# --- Quelle B Reihe ---
yB = 8.4
node(ax, 0.5, yB, 'CSV Reader (B)\nCSV export', 'reader', 1)
node(ax, 3.1, yB, 'Rule-based Row Filter\nADC ≥ 2³¹ OR ≤ 0', 'filter', 2)
node(ax, 5.7, yB, 'Normalizer\nV0 z-score / V1 SNV\nV2/V3 MSC', 'manip', 3)
conn(ax, 2.55, yB + 0.25, 3.1, yB + 0.25)
conn(ax, 5.15, yB + 0.25, 5.7, yB + 0.25)

# Metanode-Rahmen "Per-source preprocessing (A, B)"
ax.add_patch(Rectangle((0.3, yB - 0.35), 7.75, 2.2, fc='none',
                       ec='#999', lw=0.9, ls='--'))
ax.text(4.2, yB - 0.22, 'per-source preprocessing × 2 sources',
        fontsize=6, color='#777', ha='center', style='italic')

# Concatenate
node(ax, 8.4, 9.2, 'Concatenate\n(fusion, col "source")', 'manip', 4)
conn(ax, 7.75, yA + 0.25, 8.4, 9.45)
conn(ax, 7.75, yB + 0.25, 8.4, 9.35)

node(ax, 11.0, 9.2, 'X-Partitioner\n5-fold, shuffle, seed 42', 'manip', 5)
conn(ax, 10.45, 9.45, 11.0, 9.45)
node(ax, 13.6, 9.2, 'PLS Learner (Py)\n10 components', 'learner', 6)
conn(ax, 13.05, 9.45, 13.6, 9.45)
node(ax, 16.2, 9.2, 'PLS Predictor', 'learner', 7)
conn(ax, 15.65, 9.45, 16.2, 9.45)

node(ax, 18.8, 9.9, 'Numeric Scorer\nR², RMSECV', 'script', 8)
conn(ax, 18.25, 9.55, 18.8, 10.1)
node(ax, 18.8, 8.6, 'R-Snippet\nleveneTest · t.test\n(per source)', 'script', 9)
conn(ax, 18.25, 9.35, 18.8, 8.95)

# Visualisierung unten
node(ax, 11.0, 6.2, 'Scatter Plot\npredicted vs. reference', 'vis', 10)
conn(ax, 18.25, 9.3, 19.6, 9.3)
conn(ax, 19.6, 9.3, 19.6, 6.45, '--')
conn(ax, 19.6, 6.45, 13.05, 6.45)
node(ax, 13.6, 6.2, 'Bar Chart\nRMSE per variant', 'vis', 11)
conn(ax, 13.05, 6.45, 13.6, 6.45)
node(ax, 16.2, 6.2, 'Brix Band Matrix\n(per source)', 'vis', 12)
conn(ax, 15.65, 6.45, 16.2, 6.45)

# Varianten-Annotation
ax.add_patch(FancyBboxPatch((0.5, 3.4), 10.5, 1.7,
                            boxstyle='round,pad=0.2',
                            fc='#fff8e1', ec='#b8860b', lw=1))
ax.text(5.75, 4.75, 'Correction variants evaluated (identical pipeline per variant)',
        fontsize=7, fontweight='bold', ha='center')
ax.text(5.75, 4.35, 'V0 global z-score: R²cv 0.545 (Levene p=0.006, Welch p<0.001)', fontsize=6.4, ha='center')
ax.text(5.75, 4.0, 'V1 SNV: R²cv 0.646 · V2 MSC per source: 0.453 · V3 MSC anchor: 0.472', fontsize=6.4, ha='center')
ax.text(5.75, 3.65, '→ SNV improves measurably, stays below best single source (B: 0.722)', fontsize=6.4, ha='center', color='#a0522d')

# Ehrlichkeits-Annotation unten
ax.add_patch(FancyBboxPatch((0.5, 1.0), 21.0, 1.9,
                            boxstyle='round,pad=0.25',
                            fc='#f5f5f5', ec='#888', lw=1))
ax.text(11, 2.5, 'Reproducibility note', fontsize=7.5, fontweight='bold', ha='center')
ax.text(11, 2.15, 'The .knwf in the repository is a generated description of this node chain (not auto-importable; a faithful KNIME 5.x rebuild requires the full node-XML from a live KNIME instance).', fontsize=6.3, ha='center', color='#555')
ax.text(11, 1.8, 'Fully executable deterministic counterpart: scripts/knime_fusion_analysis.py (identical logic, seed 42, same numbers) — runs without KNIME.', fontsize=6.3, ha='center', color='#2e7d32')
ax.text(11, 1.45, 'Step-by-step rebuild instructions for KNIME 5.x: knime/tomato_brix_reference/README.md', fontsize=6.3, ha='center', color='#555')
ax.text(11, 0.55, 'Node shapes/ports stylized after the KNIME Analytics Platform editor; numbers = processing order; dashed frame = per-source group.',
        fontsize=6, color='#777', ha='center', style='italic')

plt.tight_layout()
plt.savefig('fig4_knime_workflow.png', dpi=300, bbox_inches='tight',
            facecolor='white')
print('fig4 PNG erzeugt')
