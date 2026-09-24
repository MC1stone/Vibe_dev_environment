#!/usr/bin/env python3
"""Erzeugt tomato_nir_brix.tab (Orange-Format) aus den Tomaten-Rohdaten.

Filter wie in der Skript-Analyse: ADC-Ueberlauf (>= 2^31) und Nullwerte raus.
Brix = Zielvariable (class), IDs/Temp = Metadaten (meta), 18 Kanaele = Attribute.
"""

import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "T4-T5_ALLE_mit_Brix_2_parsed.json")
OUT = os.path.join(BASE, "orange", "tomato_nir_brix.tab")

os.makedirs(os.path.dirname(OUT), exist_ok=True)

with open(RAW, encoding="utf-8") as f:
    d = json.load(f)

wl_cols = d["wavelength_columns"]
spectra = d["spectra"]

names = ["Brix", "Messobjekt", "Kurz", "Tomate", "Rispe", "Reihe", "Tag", "Temp0", "Temp1", "Temp2"] + wl_cols
types = ["continuous", "d", "string", "d", "d", "d", "d", "continuous", "continuous", "continuous"] + ["continuous"] * 18
flags = ["class", "meta"] * 1 + ["meta"] * 8 + [""] * 18
flags = ["class"] + ["meta"] * 9 + [""] * 18

rows = []
n_removed = 0
for s in spectra:
    vals = [float(s["spectra"][c]) for c in wl_cols]
    if any(v >= 2**31 or v <= 0 for v in vals):
        n_removed += 1
        continue
    temps = s["temperatures"]
    rows.append(
        [f"{s['brix']:g}", s["messobjekt"], s["kurz"], s["tomate"], s["rispe"], s["reihe"], s["tag"],
         f"{temps['temp0']:g}", f"{temps['temp1']:g}", f"{temps['temp2']:g}"]
        + [f"{v:g}" for v in vals]
    )

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\t".join(names) + "\n")
    f.write("\t".join(types) + "\n")
    f.write("\t".join(flags) + "\n")
    for r in rows:
        f.write("\t".join(r) + "\n")

print(f"OK: {OUT} ({len(rows)} Zeilen, {n_removed} entfernt)")
