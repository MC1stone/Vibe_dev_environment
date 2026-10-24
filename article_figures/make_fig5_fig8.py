#!/usr/bin/env python3
"""Erzeugt fig5 (Sensor-Datenbank) und fig6 (standardisierte Testeinheit)
als PNG (300 dpi) mit matplotlib. Inhalt identisch zu den SVG-Quellen."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BOX = dict(boxstyle='round,pad=0.35', fc='#eef4fb', ec='#2b6cb0', lw=1.4)
DB = dict(boxstyle='round,pad=0.35', fc='#eaf7ee', ec='#2e7d32', lw=1.4)
UI = dict(boxstyle='round,pad=0.35', fc='#fdf3e0', ec='#b8860b', lw=1.4)
OK = dict(boxstyle='round,pad=0.35', fc='#e8f8e8', ec='#2e7d32', lw=1.4)
WARN = dict(boxstyle='round,pad=0.35', fc='#fdeaea', ec='#c0392b', lw=1.4)
GRP = dict(boxstyle='round,pad=0.3', fc='none', ec='#888', lw=1, ls='--')
LBL = dict(fontsize=8.2, ha='center')


def group(ax, x, y, w, h, title):
    ax.text(x, y + h, title, fontsize=8.6, fontweight='bold', va='bottom')
    ax.add_patch(plt.Rectangle((x, y), w, h, fill=False, ec='#888',
                               lw=1, ls='--'))


# ============ FIG 5: SENSOR DATABASE ============
fig, ax = plt.subplots(figsize=(8.3, 5.5), dpi=300)
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis('off')
ax.text(5, 9.75, 'NIR-IP Sensor Database (§3.2): what the platform knows about every device',
        fontsize=10.5, fontweight='bold', ha='center')

group(ax, 0.2, 6.55, 9.6, 2.55, 'Layer 1 — Registered adapters (devices/ registry, no core changes per device)')
boxes = [
    (0.4, 'SparkFun Triad (AS7265x)', '18 fixed bands 410–940 nm', 'I2C/UART · in use (PoC)', 'capabilities + calibration contract'),
    (2.75, 'ESP32-S3 camera spectrometer', 'DIY grating + camera', 'WiFi/USB · registered', 'capabilities + calibration contract'),
    (5.1, 'DIY Matchbox spectrometer', 'slit-and-grating, smartphone', 'serial · registered', 'capabilities + calibration contract'),
    (7.45, 'Any further device', 'implement SpectrometerAdapter,', 'register MODEL_ID — done', 'no core change, no format hard-coding'),
]
for x, t, l1, l2, l3 in boxes:
    ax.text(x + 1.15, 8.6, t, bbox=BOX, fontsize=7.8, ha='center')
    ax.text(x + 1.15, 7.85, '\n'.join([l1, l2, l3]), fontsize=6.8, ha='center', color='#555')

group(ax, 0.2, 3.95, 9.6, 2.35, 'Layer 2 — Usage from the existing database (no new tables)')
boxes2 = [
    (0.4, 'Spectrum database', 'instrument_type per spectrum record', '→ spectra / projects / last used'),
    (3.55, 'Preparation reports + crew results', 'recorded settings per measurement', '→ optimization suggestions'),
    (6.7, 'Unmatched names → AI match suggestions', '"SparkFun Triad" vs. "Triad": the agent asks,', 'never silently deduplicates'),
]
for x, t, l1, l2 in boxes2:
    ax.text(x + 1.55, 5.85, t, bbox=DB, fontsize=7.8, ha='center')
    ax.text(x + 1.55, 5.1, '\n'.join([l1, l2]), fontsize=6.8, ha='center', color='#555')

group(ax, 0.2, 1.75, 9.6, 2.0, 'Layer 3 — Per-sensor information page (/projects/sensors/<name>/)')
boxes3 = [
    (0.4, 'Adapter profile', 'range, detector, interface,', 'resolution, streaming, trigger'),
    (2.75, 'Recorded settings', 'values + completeness /', 'plausibility assessment'),
    (5.1, 'Documents', 'datasheet, manual, calibration', 'certificate — any file type'),
    (7.45, 'AI summary (local)', 'Ollama on request; honest', 'fallback when unavailable'),
]
for x, t, l1, l2 in boxes3:
    ax.text(x + 1.15, 3.35, t, bbox=UI, fontsize=7.8, ha='center')
    ax.text(x + 1.15, 2.6, '\n'.join([l1, l2]), fontsize=6.8, ha='center', color='#555')

group(ax, 0.2, 0.15, 9.6, 1.45, 'Feeds back into analysis')
boxes4 = [
    (0.4, 'Metadata plausibility', 'known max values (e.g. scan count ≤ 100)'),
    (3.55, 'Fusion reference contract', 'dark/white, ≥ 50 repetitions (§6.7)'),
    (6.7, 'Intro page: device-specific guidance', 'teaches the same protocol the fusion branch enforces'),
]
for x, t, l1 in boxes4:
    ax.text(x + 1.55, 1.15, t, bbox=BOX, fontsize=7.8, ha='center')
    ax.text(x + 1.55, 0.55, l1, fontsize=6.8, ha='center', color='#555')

plt.tight_layout()
plt.savefig('fig5_sensor_database.png', dpi=300, bbox_inches='tight', facecolor='white')
plt.close()

# ============ FIG 8: STANDARDIZED TEST UNIT ============
fig, ax = plt.subplots(figsize=(8.3, 5.7), dpi=300)
ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis('off')
ax.text(5, 9.75, 'NIR-IP Standardized Test Unit (§6.7): the reference-measurement protocol contract',
        fontsize=10.5, fontweight='bold', ha='center')

group(ax, 0.2, 7.4, 9.6, 2.15, 'Contract — a measurement condition, not a device (sensor-agnostic)')
boxes = [
    (0.4, 'DARK reference', 'reference_type = "dark",', 'artifact, ≥ 50 repetitions', 'dataset_type = reference_measurement'),
    (3.55, 'WHITE reference', 'reference_type = "white",', 'artifact, ≥ 50 repetitions', 'dataset_type = reference_measurement'),
    (6.7, 'Declared as metadata at ingestion', 'no specific hardware prescribed;', 'reference datasets NEVER enter a', 'calibration — they are not samples'),
]
for x, t, l1, l2, l3 in boxes:
    ax.text(x + 1.55, 9.05, t, bbox=UI, fontsize=7.8, ha='center')
    ax.text(x + 1.55, 8.15, '\n'.join([l1, l2, l3]), fontsize=6.8, ha='center', color='#555')

group(ax, 0.2, 5.15, 9.6, 2.0, 'Radiometric evaluation (per channel, per source)')
boxes2 = [
    (0.4, 'Transfer function', 'reflectance = (raw − dark) /', '(white − dark), per channel'),
    (3.55, 'Gain curve', 'smoothed over the wavelength axis;', 'confidence note from repetition spread'),
    (6.7, 'Compliance check (sensor quality agent)', 'type + artifact + n ≥ 50 verified per source', 'before the gain curve is offered'),
]
for x, t, l1, l2 in boxes2:
    ax.text(x + 1.55, 6.75, t, bbox=BOX, fontsize=7.8, ha='center')
    ax.text(x + 1.55, 6.0, '\n'.join([l1, l2]), fontsize=6.8, ha='center', color='#555')

group(ax, 0.2, 2.9, 9.6, 2.0, 'Role in the fusion correction loop (Section 6.7)')
ax.text(1.95, 4.5, 'Contract met', bbox=OK, fontsize=7.8, ha='center')
ax.text(1.95, 3.75, 'gain curve offered as an additional\ncorrection variant (SNV, MSC, gain);\nidentical CV pipeline re-run on\ncorrected data → corrected verdict',
        fontsize=6.8, ha='center', color='#555')
ax.text(5.1, 4.5, 'Contract not met', bbox=WARN, fontsize=7.8, ha='center')
ax.text(5.1, 3.75, 'gain curve honestly reported as\n"not estimable", with the protocol text;\nit is never simulated — the tomato\nsources are the documented case',
        fontsize=6.8, ha='center', color='#555')
ax.text(8.25, 4.5, 'Common radiometric scale', bbox=BOX, fontsize=7.8, ha='center')
ax.text(8.25, 3.75, 'any device that measures the two references\ncan be placed on one scale — without\ncentralizing raw spectra; scales to every\nfuture sensor in the growing database',
        fontsize=6.8, ha='center', color='#555')

group(ax, 0.2, 0.15, 9.6, 2.5, 'Why a test unit matters in the public sector')
boxes3 = [
    (0.4, 'Comparability', 'municipal labs, schools and citizen', 'groups measure on different devices;', 'the contract makes results comparable'),
    (3.55, 'Teachability', 'the intro page teaches exactly this', 'protocol; one procedure, every device', '— the same contract fusion enforces'),
    (6.7, 'Trust without certification', 'no certified reference material is needed:', 'dark/white are reproducible by anyone, and', 'the repetition spread states the confidence'),
]
for x, t, l1, l2, l3 in boxes3:
    ax.text(x + 1.55, 2.25, t, bbox=DB, fontsize=7.8, ha='center')
    ax.text(x + 1.55, 1.4, '\n'.join([l1, l2, l3]), fontsize=6.8, ha='center', color='#555')

plt.tight_layout()
plt.savefig('fig8_test_unit.png', dpi=300, bbox_inches='tight', facecolor='white')
plt.close()
print('fig5 + fig6 written')
