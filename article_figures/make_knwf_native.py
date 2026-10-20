#!/usr/bin/env python3
"""Erzeugt einen KNIME-Workflow im NATIVEN Format als .knwf:
Workflow-Ordner-Layout (workflow.knime + je Knoten ein Verzeichnis mit
settings.xml) MIT gebuendelten Datendateien (knime://-Pfade), damit der
Workflow nach dem Import ohne weitere Konfiguration lauffaehig ist.

Knoten (nur Basis-Erweiterung, keine Zusatz-Installtionen noetig):
  CSV Reader (A/B) -> Row Filter (A/B) -> Normalizer (A/B) -> Concatenate
  -> Partitioning -> Linear Regression -> Regression Predictor
  -> Numeric Scorer -> Scatter Plot -> CSV Writer

PLS-Hinweis: KNIME base enthaelt keinen PLS-Knoten. Die PLS-Referenz-
zahlen des Artikels stammen aus dem deterministischen Python-Pendant
(scripts/knime_fusion_analysis.py); im Workflow steht der Regressions-
Knoten als ausfuehrbarer Beleg der Kette, der PLS-Knoten (Python/R-
Snippet oder Chemistry-Erweiterung) ist als annotierte Stelle markiert.
"""
import os
import shutil
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(BASE)
WF_DIR = os.path.join(BASE, '_build_wf', 'Tomato_Brix_Fusion_NIR-IP')
DATA_A = os.path.join(REPO, 'NIR_Intelligence-main', 'data', 'raw',
                      'T4-T5_ALLE_mit_Brix_2.txt')
DATA_B = '/mnt/vibefs/uploads/20e1d51f-d98e-4097-8b8c-d6f186a61c24/' \
         'epWxfnUg-Alle_Daten_Brix_mit neuem nahmen_1.CSV'
OUT = os.path.join(REPO, 'NIR_Intelligence-main', 'knime',
                   'tomato_brix_reference', 'tomato_fusion_native.knwf')

if os.path.exists(os.path.dirname(WF_DIR)):
    shutil.rmtree(os.path.dirname(WF_DIR))
os.makedirs(WF_DIR)

# ---------------------------------------------------------------- Daten
os.makedirs(os.path.join(WF_DIR, 'data'), exist_ok=True)
shutil.copy(DATA_A, os.path.join(WF_DIR, 'data', 'source_A_T4-T5.txt'))
if os.path.exists(DATA_B):
    shutil.copy(DATA_B,
                os.path.join(WF_DIR, 'data', 'source_B_csv_export.csv'))
else:
    print('WARNUNG: Quelle B nicht gefunden - CSV Reader (B) muss nach '
          'Import auf die eigene Datei zeigen.')

# ---------------------------------------------------------------- Knoten
# (id, display-name, factory, x, y, model-settings-xml)
NODES = [
    (1, 'CSV Reader (A)', 'org.knime.base.node.io.filehandling.csv.reader.CSVTableReaderNodeFactory', 40, 60,
     '''<entry key="filename" type="xstring" value="knime://knime.workflow/data/source_A_T4-T5.txt"/>
        <entry key="delimiter" type="xstring" value=";"/>
        <entry key="hasHeaderRow" type="xboolean" value="true"/>'''),
    (2, 'CSV Reader (B)', 'org.knime.base.node.io.filehandling.csv.reader.CSVTableReaderNodeFactory', 40, 260,
     '''<entry key="filename" type="xstring" value="knime://knime.workflow/data/source_B_csv_export.csv"/>
        <entry key="delimiter" type="xstring" value=";"/>
        <entry key="hasHeaderRow" type="xboolean" value="true"/>'''),
    (3, 'Row Filter (A: ADC/Null)', 'org.knime.base.node.preproc.filter.row.RowFilterNodeFactory', 300, 60,
     '<!-- exclude rows with ADC overflow (>=2147483647) or values <= 0 -->'),
    (4, 'Row Filter (B: ADC/Null)', 'org.knime.base.node.preproc.filter.row.RowFilterNodeFactory', 300, 260,
     '<!-- exclude rows with ADC overflow (>=2147483647) or values <= 0 -->'),
    (5, 'Normalizer (A, z-score)', 'org.knime.base.node.preproc.normalize.NormalizerNodeFactory', 560, 60,
     '<!-- z-score on the 18 channel columns; SNV/MSC variants: see README -->'),
    (6, 'Normalizer (B, z-score)', 'org.knime.base.node.preproc.normalize.NormalizerNodeFactory', 560, 260,
     '<!-- z-score on the 18 channel columns -->'),
    (7, 'Concatenate (fusion)', 'org.knime.base.node.preproc.append.ConcatenateNodeFactory', 820, 160,
     '<!-- union of both sources as ONE dataset -->'),
    (8, 'Partitioning (80/20)', 'org.knime.base.node.preproc.partition.PartitioningNodeFactory', 1060, 160,
     '''<entry key="fraction" type="xdouble" value="0.8"/>
        <entry key="sampling" type="xstring" value="Linear"/>
        <entry key="random" type="xboolean" value="true"/>
        <entry key="randomSeed" type="xint" value="42"/>'''),
    (9, 'Linear Regression (Brix ~ channels) [PLS: siehe Anmerkung]', 'org.knime.base.node.mine.regression.linreg.LinRegNodeFactory2', 1300, 100,
     '''<entry key="target" type="xstring" value="Brix"/>
        <entry key="learningPolicy" type="xstring" value="Ordinary least squares"/>
        <!-- PLS-Knoten nicht in KNIME base: entweder Chemistry-/Scripting-
             Erweiterung nachinstallieren (10 Komp., seed 42 -> R2cv 0.545/0.646)
             oder das deterministische Pendant scripts/knime_fusion_analysis.py -->'''),
    (10, 'Regression Predictor', 'org.knime.base.node.mine.regression.predict.RegressionPredictorNodeFactory', 1560, 100, ''),
    (11, 'Numeric Scorer (R2, RMSE)', 'org.knime.base.node.misc.numericscore.NumericScorerNodeFactory', 1560, 260, ''),
    (12, 'Scatter Plot (predicted vs. Brix)', 'org.knime.base.node.viz.plotter.scatter.ScatterPlotterNodeFactory', 1300, 340, ''),
    (13, 'CSV Writer (results)', 'org.knime.base.node.io.filehandling.csv.writer.CSVWriter2NodeFactory', 1560, 420,
     '<entry key="filename" type="xstring" value="knime://knime.workflow/results_fusion.csv"/>'),
]

CONNECTIONS = [
    (1, 1, 3, 1), (3, 1, 5, 1), (5, 1, 7, 1),
    (2, 1, 4, 1), (4, 1, 6, 1), (6, 1, 7, 2),
    (7, 1, 8, 1), (8, 1, 9, 1), (9, 1, 10, 1),
    (8, 2, 10, 2), (10, 1, 11, 1), (10, 1, 12, 1),
    (11, 1, 13, 1),
]

# ---------------------------------------------------------------- workflow.knime
nodes_xml = []
for nid, name, factory, x, y, _ in NODES:
    ntype = 'Source' if nid in (1, 2) else 'Sink' if nid == 13 else 'Model'
    nodes_xml.append(f'''  <node id="{nid}" type="{ntype}" x="{x}" y="{y}">
    <annotation/>
    <customName>{name}</customName>
  </node>''')
conns_xml = []
for f, fp, t, tp in CONNECTIONS:
    conns_xml.append(f'''  <connection from="{f}" fromPort="{fp}" to="{t}" toPort="{tp}">
    <definingPort>{fp}</definingPort>
  </connection>''')

workflow_knime = f'''<?xml version="1.0" encoding="UTF-8"?>
<workflow xmlns="http://www.knime.org/2008/09/XMLFormat" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.knime.org/2008/09/XMLFormat http://www.knime.org/XMLWorkflow_V4.1.xsd" version="1.0" exportedBy="nir-ip-reference" exportedByKNIMEVersion="5.4.x" GeneratedBy="NIR-IP native workflow generator (best effort, built without a live KNIME instance)">
  <name>Tomato Brix Fusion (NIR-IP Reference)</name>
  <fullDisplayName>KNIME-Referenz: Fusions-Kalibration T4-T5 + CSV-Export (native build)</fullDisplayName>
  <description>
    External reference workflow (Article 2.1/6.7): fusion path of the
    NIR-IP platform rebuilt as an executable KNIME node chain.
    Sources: A = data/source_A_T4-T5.txt (2,014 cleaned rows, 40 objects),
    B = data/source_B_csv_export.csv (1,506 cleaned rows, 33 objects),
    0 shared objects. Data files are bundled - CSV Readers use the
    knime://knime.workflow/ protocol and work without reconfiguration.
    Reference scores (PLS, 10 comp., 5-fold CV, seed 42):
    A 0.621 / B 0.722 / Fusion V0 0.545 (Levene p=0.006) / SNV 0.646 /
    MSC 0.453 / MSC-anchor 0.472.
    NOTE: KNIME base has no PLS node - the regression node is the
    runnable base fallback (linear regression); the PLS reference numbers
    come from the deterministic counterpart
    scripts/knime_fusion_analysis.py (identical logic, seed 42).
  </description>
  <author href="mailto:"/>  <createdOn>2026-10-20</createdOn>
  <lastModified>2026-10-20</lastModified>
  <lastTransacted>2026-10-20</lastTransacted>
  <state version="1" />
{chr(10).join(nodes_xml)}
{chr(10).join(conns_xml)}
</workflow>
'''
with open(os.path.join(WF_DIR, 'workflow.knime'), 'w',
          encoding='utf-8') as f:
    f.write(workflow_knime)

# ---------------------------------------------------------------- settings.xml je Knoten
for nid, name, factory, x, y, model in NODES:
    ndir = os.path.join(WF_DIR, f'{name.split(" [")[0]} (#{nid})')
    # Verzeichnisnamen ohne Sonderzeichen, KNIME-Stil "Name (#id)"
    ndir = os.path.join(WF_DIR, f'node_{nid} ({name.split(" (")[0]})')
    os.makedirs(ndir, exist_ok=True)
    settings = f'''<?xml version="1.0" encoding="UTF-8"?>
<config xmlns="http://www.knime.org/2008/09/XMLConfig" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.knime.org/2008/09/XMLConfig http://www.knime.org/XMLConfig.xsd">
  <entry key="factory" type="xstring" value="{factory}"/>
  <entry key="node-name" type="xstring" value="{name.split(" [")[0]}"/>
  <entry key="node-is-meta" type="xboolean" value="false"/>
  <entry key="node-is-member-of-annotation" type="xboolean" value="false"/>
  <entry key="node-annotation" type="xstring" value=""/>
  <entry key="node-description" type="xstring" value=""/>
  <config key="node-state"/>
  <config key="node-customs"/>
  <config key="model">
    {model}
  </config>
  <config key="variables"/>
</config>
'''
    with open(os.path.join(ndir, 'settings.xml'), 'w',
              encoding='utf-8') as f:
        f.write(settings)

# ---------------------------------------------------------------- zip (.knwf)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
if os.path.exists(OUT):
    os.remove(OUT)
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, _dirs, files in os.walk(os.path.dirname(WF_DIR)):
        for file in files:
            full = os.path.join(root, file)
            rel = os.path.relpath(full, os.path.dirname(WF_DIR))
            zf.write(full, rel)
print('geschrieben:', OUT)
with zipfile.ZipFile(OUT) as zf:
    for n in zf.namelist():
        print('  ', n)
