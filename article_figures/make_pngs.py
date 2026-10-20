#!/usr/bin/env python3
"""Erzeugt die drei Artikel-Grafiken als PNG (300 dpi) mit matplotlib.
Inhalt identisch zu den SVG-Quellen (fig1/fig2/fig3)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

BOX = dict(boxstyle='round,pad=0.35', fc='#e8f1fb', ec='#2b6cb0', lw=1.4)
DEC = dict(boxstyle='round,pad=0.35', fc='#fff6e0', ec='#b8860b', lw=1.4)
OK = dict(boxstyle='round,pad=0.35', fc='#e8f8e8', ec='#2e7d32', lw=1.4)
WARN = dict(boxstyle='round,pad=0.35', fc='#fdeaea', ec='#c0392b', lw=1.4)
GRP = dict(boxstyle='round,pad=0.3', fc='none', ec='#888', lw=1, ls='--')
SMALL = dict(fontsize=7.2, color='#555', ha='center')
LBL = dict(fontsize=8.2, ha='center')


def arrow(ax, x1, y1, x2, y2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='-|>', color='#333', lw=1.3))


# ============ FIG 1: FUSION FLOWCHART ============
fig, ax = plt.subplots(figsize=(8.3, 6.4), dpi=300)
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis('off')
ax.text(5, 9.7, 'NIR-IP Fusion Branch: Review-Governed Workflow (Section 6.7)',
        fontsize=10.5, fontweight='bold', ha='center')

steps = [
    (5, 8.9, 'Similarity search: hits from ANOTHER project'),
    (5, 7.9, 'Field-wise metadata comparison\n(generic — no domain hard-coding)'),
    (5, 6.85, 'Fusion into a NEW project\noriginals untouched · double-fusion guard (422)'),
    (5, 5.7, 'Comparative calibration: 3 × PLS + significance test\nsource A · source B · combined — Levene + Welch'),
]
for i, (x, y, t) in enumerate(steps):
    ax.text(x, y, t, bbox=BOX, **LBL)
    arrow(ax, x, y - 0.28, x, steps[i + 1][1] + 0.3) if i < 3 else None
arrow(ax, 5, 5.4, 5, 4.8)

ax.text(5, 4.5, 'Residual heterogeneity?', bbox=DEC, **LBL)
# no-Zweig
arrow(ax, 3.9, 4.5, 2.2, 4.5)
ax.text(3.0, 4.62, 'no', fontsize=8)
ax.text(1.5, 4.5, 'Fusion verdict:\ngain', bbox=OK, **LBL)
# yes-Zweig
arrow(ax, 6.1, 4.5, 7.6, 4.5)
ax.text(6.85, 4.62, 'yes', fontsize=8)
ax.text(8.1, 4.5, 'Correction loop\nSNV · MSC · gain curve*', bbox=WARN, **LBL)
arrow(ax, 8.1, 4.1, 8.1, 3.5)
ax.text(8.1, 3.1, 'Re-evaluation on corrected data —\ncorrected verdict\n(first-class negative results,\nnever simulated)', bbox=BOX, **LBL)
arrow(ax, 8.1, 2.15, 8.1, 1.65)
ax.text(8.1, 1.25, 'Corrected fusion ≥ best\nsingle source?\nyes → fusion is an option\nno → per source + reference\nprotocol (≥ 50) → re-fuse',
        bbox=DEC, fontsize=7.6, ha='center')
ax.text(5, 0.25, '* gain curve requires compliant dark/white reference measurements (reference protocol contract)',
        **SMALL)
plt.tight_layout()
plt.savefig('fig1_fusion_flowchart.png', dpi=300, bbox_inches='tight',
            facecolor='white')
plt.close()

# ============ FIG 2: COMPONENTS ============
fig, ax = plt.subplots(figsize=(9, 5.6), dpi=300)
ax.set_xlim(0, 12); ax.set_ylim(0, 8); ax.axis('off')
ax.text(6, 7.75, 'NIR-IP Platform: Components & Capabilities (Article §3)',
        fontsize=10.5, fontweight='bold', ha='center')

agents = [
    ('Metadata\nAgent', 'FAIR / ISO 19115\nscorecard'), ('Sensor\nQuality', 'noise, drift,\nSNR, ADC, AE'),
    ('Statistical\nAnalysis', 'PCA · PLS · PCR\nANOVA · clust.'), ('Neural\nNetwork', 'CNN · MLP · AE\nalways parallel'),
    ('Calibration', '6 methods\nRMSECV, RPD'), ('FAISS /\nQdrant', 'similarity →\nfusion trigger'),
    ('LLM Reasoning', 'Ollama/Mistral\nRAG chatbot'), ('Flower FL', 'FedAvg/FedProx\nDP, consent'),
    ('Quarto Report', 'charts, iteration\narchive'), ('Sensor\nCatalog', 'adapters, ref.\ncontract'),
]
ax.text(0.3, 7.35, 'Analysis Agents (CrewAI-orchestrated, every project run)',
        fontsize=8, fontweight='bold')
ax.add_patch(FancyBboxPatch((0.15, 2.9), 11.7, 4.2, **GRP))
for i, (name, sub) in enumerate(agents):
    col, row = i % 5, i // 5
    x, y = 0.45 + col * 2.3, 6.55 - row * 1.75
    ax.text(x, y, name, fontsize=7.6, fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.3', fc='#eef4fb', ec='#2b6cb0'))
    ax.text(x, y - 0.55, sub, fontsize=6.2, color='#555', ha='center')

ax.text(0.3, 2.6, 'Fusion Branch Services (OP63–OP71, fusion projects only)',
        fontsize=8, fontweight='bold')
ax.add_patch(FancyBboxPatch((0.15, 0.9), 11.7, 1.85, **GRP))
fusion = [
    ('project_fusion', 'merge, provenance,\nguard, suggestions'), ('fusion_calibration', '3×PLS + Levene/Welch,\nhit quotas, band matrix'),
    ('fusion_sensor_analysis', 'sensor comparison,\nconfounding, gain curve'), ('correction loop', 'SNV · MSC · gain,\nverdict, chatbot'),
]
for i, (name, sub) in enumerate(fusion):
    x = 1.5 + i * 2.9
    ax.text(x, 2.2, name, fontsize=7, fontweight='bold', ha='center',
            bbox=dict(boxstyle='round,pad=0.3', fc='#fdf3e0', ec='#b8860b'))
    ax.text(x, 1.6, sub, fontsize=6, color='#555', ha='center')

ax.text(6, 0.55, 'External References (validation only — never part of the app):  '
        'Orange (PLS 0.622) · KNIME (0.621, fusion counter-check) · '
        'deterministic test matrices (OP63–OP72, FL1–FL6, S9 — all green in CI)',
        fontsize=6.4, color='#2e7d32', ha='center',
        bbox=dict(boxstyle='round,pad=0.25', fc='#eaf7ee', ec='#2e7d32'))
plt.tight_layout()
plt.savefig('fig2_components.png', dpi=300, bbox_inches='tight',
            facecolor='white')
plt.close()

# ============ FIG 3: CORRECTION LOOP ============
fig, ax = plt.subplots(figsize=(8.6, 4.3), dpi=300)
ax.set_xlim(0, 12); ax.set_ylim(0, 7); ax.axis('off')
ax.text(6, 6.75, 'Correction Loop on Real Source Pair — Measured Outcome (Section 6.7, Table 9)',
        fontsize=9.5, fontweight='bold', ha='center')

ax.text(1.6, 5.8, 'Fusion baseline V0\nR²cv 0.545\nLevene p=0.006', bbox=BOX, fontsize=7.6, ha='center')
arrow(ax, 2.6, 5.8, 3.4, 5.8)
ax.text(4.5, 5.8, 'Apply corrections\nSNV · MSC per source ·\nMSC shared anchor', bbox=DEC, fontsize=7, ha='center')
arrow(ax, 5.6, 5.8, 6.4, 5.8)
ax.text(7.4, 5.8, 'Best: SNV\nR²cv 0.646\nhit ±0.5: 51%→60%', bbox=OK, fontsize=7.6, ha='center')
arrow(ax, 8.5, 5.8, 9.2, 5.8)
ax.text(10.3, 5.8, 'MSC variants\n0.453 / 0.472\nno improvement', bbox=WARN, fontsize=7, ha='center')

ax.text(2.8, 3.5, 'Corrected verdict (automatic)\n"SNV improves the fusion measurably\n(0.545 → 0.646), remains below the best\nsingle source (0.722) — calibrate per\nsource or acquire reference measurements."',
        bbox=BOX, fontsize=6.8, ha='center')
arrow(ax, 7.4, 5.15, 7.0, 4.3)
arrow(ax, 6.2, 4.0, 5.2, 3.9)

ax.text(8.9, 3.3, 'Why correction is not enough (measured)\n· Levene under SNV: p < 0.001 (stronger!)\n· 10/18 channels significantly different\n· ratio G_560: 0.52 · structure |Δ| 0.64\n· gain ↔ sample confounding (IQR 2.2)\n→ only the reference protocol resolves it',
        bbox=BOX, fontsize=6.8, ha='center')
arrow(ax, 8.9, 4.35, 8.9, 4.15)

ax.text(6, 1.15, 'Future work: reference protocol → empirically validated gain correction\n'
        'Acquire dark/white references (≥ 50 repetitions per source, declared as metadata)\n'
        '→ platform estimates the sensor transfer function radiometrically: (raw − dark)/(white − dark)\n'
        '→ gain-curve correction variant → re-run fusion → Table 9 result row (scheduled loop iteration)',
        bbox=DEC, fontsize=6.8, ha='center')
plt.tight_layout()
plt.savefig('fig3_correction_loop.png', dpi=300, bbox_inches='tight',
            facecolor='white')
plt.close()
print('3 PNGs erzeugt')
