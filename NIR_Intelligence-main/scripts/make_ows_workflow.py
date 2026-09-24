#!/usr/bin/env python3
"""Erzeugt die Orange-Workflow-Datei tomato_nir_brix_analysis.ows.

Der Workflow bildet das gestern vorgeschlagene Orange-ML-Setup ab:
Datenvorbereitung, Qualitaetspruefung, Spektralanalyse, Statistik (PCA/PLS/
Clustering/ANOVA), Neuronale Netze (MLP + Python-Skript), XAI, Kalibrierung,
Bericht. Widgets ohne GUI-Serialisierbarkeit (z. B. TF-CNN) laufen im
Python-Script-Widget.
"""

import base64
import os
import pickle
from xml.sax.saxutils import escape


class RecentPath:
    """Platzhalter mit dem Modulpfad der echten Orange-Klasse.

    Pickle speichert nur den qualifizierten Klassennamen plus __dict__;
    beim Laden in Orange wird die echte Klasse aus
    orangewidget.utils.filedialogs importiert.
    """

    def __init__(self, abspath, prefix, relpath, title="", sheet="", file_format=None):
        self.abspath = abspath
        self.prefix = prefix
        self.relpath = relpath
        self.title = title
        self.sheet = sheet
        self.file_format = file_format


RecentPath.__module__ = "orangewidget.utils.filedialogs"

import sys  # noqa: E402
import types  # noqa: E402

_pkg = types.ModuleType("orangewidget")
_pkg_utils = types.ModuleType("orangewidget.utils")
_mod = types.ModuleType("orangewidget.utils.filedialogs")
_mod.RecentPath = RecentPath
sys.modules["orangewidget"] = _pkg
sys.modules["orangewidget.utils"] = _pkg_utils
sys.modules["orangewidget.utils.filedialogs"] = _mod

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "orange", "tomato_nir_brix_analysis.ows")

SCRIPT_QUALITY = r'''import numpy as np
from Orange.data import Table

# Qualitaetsbewertung: Rauschen (CV der Wiederholungen je Tomate),
# Drift (Trend ueber Messreihenfolge), SNR und Ampel-Score
data = in_data
X = data.X
names = [a.name for a in data.domain.attributes]
meta_names = [m.name for m in data.domain.metas]
tomate_idx = meta_names.index("Tomate") if "Tomate" in meta_names else None

groups = [row["Tomate"].value for row in data] if tomate_idx is not None else [str(i) for i in range(len(X))]

uniq = sorted(set(groups))
noise, snr = [], []
for g in uniq:
    mask = [i for i, gg in enumerate(groups) if gg == g]
    Xg = X[mask]
    noise.append(Xg.std(axis=0).mean() / max(Xg.mean(axis=0).mean(), 1e-9))
    snr.append((Xg.mean(axis=0) / Xg.std(axis=0)).mean())
noise_level = float(np.mean(noise))
snr_median = float(np.median(snr))

mean_int = X.mean(axis=1)
drift = float(abs(np.polyfit(np.arange(len(mean_int)), mean_int, 1)[0])) / max(mean_int.mean(), 1e-9)

score = max(0.0, 1 - noise_level / 0.05 * 0.5 - drift / 0.01 * 0.5)
ampel = "GRUEN" if score > 0.7 else ("GELB" if score > 0.4 else "ROT")

print("Rauschen (CV): %.4f (Schwelle 0.05)" % noise_level)
print("Drift (relativ): %.4f (Schwelle 0.01)" % drift)
print("SNR Median: %.2f" % snr_median)
print("Qualitaets-Score: %.3f -> %s" % (score, ampel))
if noise_level > 0.05:
    print("WARNUNG: Rauschen > 0.05 - Messzeit erhoehen / Wiederholungen mitteln")
if drift > 0.01:
    print("WARNUNG: Drift > 0.01 - Geraet neu kalibrieren")

out_data = in_data
out_object = {"rauschen": noise_level, "drift": drift, "snr": snr_median,
              "score": score, "ampel": ampel}
'''

SCRIPT_XAI = r'''import numpy as np
from sklearn.inspection import permutation_importance
from Orange.data import Table, Domain, ContinuousVariable
from Orange.regression import PLSRegressionLearner

# XAI: Permutationswichtigkeit je Kanal (SHAP-analog, modellunabhaengig)
data = in_data
X, y = data.X, data.Y.ravel()
names = [a.name for a in data.domain.attributes]

learner = PLSRegressionLearner(n_components=9)
model = learner(data)

# permutation importance ueber Shuffle der Spalten (R2-Abfall)
from Orange.evaluation import CrossValidation, RMSE
rng = np.random.RandomState(42)
baseline_pred = model(data)
try:
    base_r2 = 1 - np.sum((y - baseline_pred) ** 2) / np.sum((y - y.mean()) ** 2)
except Exception:
    base_r2 = np.nan

imp = []
for j in range(X.shape[1]):
    Xp = X.copy()
    rng.shuffle(Xp[:, j])
    dperm = Table(Domain(data.domain.attributes, data.domain.class_var), Xp, y)
    pred = model(dperm)
    try:
        r2 = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
        imp.append(base_r2 - r2)
    except Exception:
        imp.append(0.0)

order = np.argsort(-np.array(imp))
print("XAI - Kanalwichtigkeit (R2-Abfall bei Vertauschung):")
for i in order[:8]:
    print("  %s: %.4f" % (names[i], imp[i]))

out_data = in_data
out_object = {"wichtigkeit": {names[i]: float(imp[i]) for i in order[:8]},
              "basis_r2": float(base_r2)}
'''

SCRIPT_FAISS = r'''import numpy as np
from Orange.data import Table, Domain, ContinuousVariable

# FAISS: Top-3 aehnlichste Spektren (hier via L2 auf SNV-Daten)
try:
    import faiss
    HAVE_FAISS = True
except ImportError:
    HAVE_FAISS = False

data = in_data
X = data.X.astype(np.float32)
names = [a.name for a in data.domain.attributes]

# SNV pro Spektrum
mu = X.mean(axis=1, keepdims=True)
sd = X.std(axis=1, keepdims=True)
Xsnv = (X - mu) / np.maximum(sd, 1e-9)

q = 0
if HAVE_FAISS:
    index = faiss.IndexFlatL2(Xsnv.shape[1])
    index.add(Xsnv)
    D, I = index.search(Xsnv[q:q+1], 4)
    top = [(int(i), float(d)) for i, d in zip(I[0][1:], D[0][1:])]
else:
    d2 = np.sum((Xsnv - Xsnv[q]) ** 2, axis=1)
    idx = np.argsort(d2)
    top = [(int(i), float(np.sqrt(d2[i]))) for i in idx[1:4]]

print("FAISS: Top-3 aehnlichste Spektren zu Messung 0:")
for rank, (i, dk) in enumerate(top, 1):
    print("  #%d: Zeile %d (D=%.3f)" % (rank, i, dk))

out_data = in_data
out_object = {"top3": top, "faiss_verfuegbar": HAVE_FAISS}
'''


def pickle_props(obj):
    return base64.encodebytes(pickle.dumps(obj, protocol=4)).decode("ascii")


class Workflow:
    def __init__(self):
        self.nodes = []
        self.links = []
        self.props = []
        self._link_id = 0

    def node(self, name, qname, pos, title=None, props=None, fmt="literal"):
        nid = len(self.nodes)
        self.nodes.append((nid, name, qname, pos, title or name))
        if props is not None:
            data = pickle_props(props) if fmt == "pickle" else escape(props)
            self.props.append((nid, fmt, data))
        return nid

    def link(self, src, dst, src_ch="Data", dst_ch="Data", src_id="data", dst_id="data"):
        lid = self._link_id
        self._link_id += 1
        self.links.append((lid, src, dst, src_ch, dst_ch, src_id, dst_id))
        return lid


w = Workflow()

# ---------------------------------------------------------------- Datei laden
file_node = w.node(
    "File", "Orange.widgets.data.owfile.OWFile", "(40, 40)",
    props={
        "recent_paths": [RecentPath("tomato_nir_brix.tab", "basedir", "tomato_nir_brix.tab")],
        "recent_urls": [],
    },
    fmt="pickle",
)

# ---------------------------------------------------- Datenvorbereitung
# Preprocess: Standardisierung (mu=0, sigma=1)
prep_node = w.node(
    "Preprocess", "Orange.widgets.data.owpreprocess.OWPreprocess", "(40, 160)",
    props=(
        "{'auto_commit': True, 'storedsettings': {'name': '', 'preprocessors': "
        "[('orange.preprocess.scale', {'method': 2})]}, '__version__': 1}"
    ),
)
w.link(file_node, prep_node)

# Select Columns: alle 18 Kanaele als Features, Brix als Target
select_node = w.node(
    "Select Columns", "Orange.widgets.data.owselectcolumns.OWSelectColumns", "(40, 280)",
    props=(
        "{'auto_commit': True, 'controlAreaVisible': True, 'savedWidgetGeometry': None, "
        "'domain': [[], [], ['Messobjekt', 'Kurz', 'Tomate', 'Rispe', 'Reihe', 'Tag', "
        "'Temp0', 'Temp1', 'Temp2'], []], '__version__': 2}"
    ),
)
w.link(prep_node, select_node)

# ---------------------------------------------------- Qualitaet (Python)
pyq = w.node(
    "Python Script (Qualität)", "Orange.widgets.data.owpythonscript.OWPythonScript",
    "(40, 420)",
    props={
        "__version__": 2,
        "scriptLibrary": [{"name": "Qualität", "script": SCRIPT_QUALITY, "filename": None}],
        "currentScriptIndex": 0,
        "scriptText": SCRIPT_QUALITY,
    },
    fmt="pickle",
)
w.link(select_node, pyq, src_ch="Data", dst_ch="Data")

# ---------------------------------------------------- Visualisierung
line_plot = w.node(
    "Line Plot", "Orange.widgets.visualize.owlineplot.OWLinePlot", "(240, 40)",
    props=(
        "{'auto_commit': True, 'show_profiles': True, 'show_mean': True, "
        "'show_range': True, 'group_var': None, '__version__': 1}"
    ),
)
w.link(select_node, line_plot)

box_plot = w.node(
    "Box Plot", "Orange.widgets.visualize.owboxplot.OWBoxPlot", "(240, 160)",
    props="{'auto_commit': True, '__version__': 1}",
)
w.link(select_node, box_plot)

distr = w.node(
    "Distributions", "Orange.widgets.visualize.owdistributions.OWDistributions", "(240, 280)",
    props="{'auto_commit': True, '__version__': 1}",
)
w.link(select_node, distr)

feature_stats = w.node(
    "Feature Statistics", "Orange.widgets.data.owfeaturestatistics.OWFeatureStatistics",
    "(240, 400)",
    props="{'auto_commit': True, '__version__': 1}",
)
w.link(select_node, feature_stats)

# ---------------------------------------------------- Statistik
pca = w.node(
    "PCA", "Orange.widgets.unsupervised.owpca.OWPCA", "(460, 40)",
    props=(
        "{'auto_commit': True, 'ncomponents': 10, 'maxp': 20, 'normalize': True, "
        "'variance_covered': 35, 'axis_labels': 10, 'controlAreaVisible': True, "
        "'savedWidgetGeometry': None, '__version__': 1}"
    ),
)
w.link(select_node, pca)

pca_plot = w.node(
    "Scatter Plot (PCA)", "Orange.widgets.visualize.owscatterplot.OWScatterPlot", "(680, 40)",
    props="{'auto_commit': True, '__version__': 1}",
)
w.link(pca, pca_plot, src_ch="Transformed Data", dst_ch="Data", src_id="transformed_data", dst_id="data")

corr = w.node(
    "Correlations", "Orange.widgets.data.owcorrelations.OWCorrelations", "(460, 160)",
    props="{'auto_commit': True, '__version__': 1}",
)
w.link(select_node, corr)

dist = w.node(
    "Distances", "Orange.widgets.unsupervised.owdistances.OWDistances", "(460, 280)",
    props=(
        "{'auto_commit': True, 'metric_idx': 0, 'normalize': False, 'axis': 0, "
        "'savedWidgetGeometry': None, '__version__': 2}"
    ),
)
w.link(select_node, dist)

hier = w.node(
    "Hierarchical Clustering", "Orange.widgets.unsupervised.owhierarchicalclustering.OWHierarchicalClustering",
    "(680, 280)",
    props=(
        "{'linkage': 4, 'annotation': 'Enumeration', 'pruning': 0, "
        "'savedWidgetGeometry': None, '__version__': 1}"
    ),
)
w.link(dist, hier, src_ch="Distances", dst_ch="Distances", src_id="distances", dst_id="distances")

# ---------------------------------------------------- Modelle
pls = w.node(
    "PLS", "Orange.widgets.model.owpls.OWPLS", "(460, 400)",
    props=(
        "{'auto_apply': True, 'n_components': 9, 'max_iter': 500, 'scale': True, "
        "'learner_name': 'PLS 9', '__version__': 1}"
    ),
)
w.link(select_node, pls, src_ch="Data", dst_ch="Data")

nn = w.node(
    "Neural Network", "Orange.widgets.model.owneuralnetwork.OWNNLearner", "(460, 520)",
    props=(
        "{'auto_apply': True, 'hidden_layers_input': '100,', 'activation_index': 3, "
        "'solver_index': 2, 'max_iterations': 200, 'alpha_index': 1, 'replicable': True, "
        "'learner_name': 'MLP', '__version__': 1}"
    ),
)
w.link(select_node, nn, src_ch="Data", dst_ch="Data")

lin = w.node(
    "Linear Regression", "Orange.widgets.model.owlinearregression.OWLinearRegression", "(460, 640)",
    props="{'auto_apply': True, 'learner_name': 'LinReg', '__version__': 1}",
)
w.link(select_node, lin, src_ch="Data", dst_ch="Data")

test_score = w.node(
    "Test and Score", "Orange.widgets.evaluate.owtestandscore.OWTestAndScore", "(700, 520)",
    props=(
        "{'resampling': 0, 'n_folds': 2, 'cv_stratified': True, 'n_repeats': 3, "
        "'sample_size': 9, 'shuffle_stratified': True, '__version__': 4}"
    ),
)
w.link(select_node, test_score, src_ch="Data", dst_ch="Data", dst_id="train_data")
w.link(pls, test_score, src_ch="Learner", dst_ch="Learner", src_id="learner", dst_id="learner")
w.link(nn, test_score, src_ch="Learner", dst_ch="Learner", src_id="learner", dst_id="learner")
w.link(lin, test_score, src_ch="Learner", dst_ch="Learner", src_id="learner", dst_id="learner")

preds = w.node(
    "Predictions", "Orange.widgets.evaluate.owpredictions.OWPredictions", "(940, 520)",
    props="{'auto_commit': True, '__version__': 1}",
)
w.link(select_node, preds, src_ch="Data", dst_ch="Data")
w.link(pls, preds, src_ch="Model", dst_ch="Predictors", src_id="model", dst_id="predictors")
w.link(nn, preds, src_ch="Model", dst_ch="Predictors", src_id="model", dst_id="predictors")

perm_plot = w.node(
    "Permutation Plot", "Orange.widgets.evaluate.owpermutationplot.OWPermutationPlot", "(940, 400)",
    props="{'n_permutations': 20, '__version__': 1}",
)
w.link(select_node, perm_plot, src_ch="Data", dst_ch="Data")
w.link(pls, perm_plot, src_ch="Learner", dst_ch="Learner", src_id="learner", dst_id="learner")

# ---------------------------------------------------- XAI + FAISS (Python)
py_xai = w.node(
    "Python Script (XAI)", "Orange.widgets.data.owpythonscript.OWPythonScript", "(40, 560)",
    props={
        "__version__": 2,
        "scriptLibrary": [{"name": "XAI", "script": SCRIPT_XAI, "filename": None}],
        "currentScriptIndex": 0,
        "scriptText": SCRIPT_XAI,
    },
    fmt="pickle",
)
w.link(select_node, py_xai)

py_faiss = w.node(
    "Python Script (FAISS)", "Orange.widgets.data.owpythonscript.OWPythonScript", "(40, 700)",
    props={
        "__version__": 2,
        "scriptLibrary": [{"name": "FAISS", "script": SCRIPT_FAISS, "filename": None}],
        "currentScriptIndex": 0,
        "scriptText": SCRIPT_FAISS,
    },
    fmt="pickle",
)
w.link(select_node, py_faiss)

# ---------------------------------------------------- Ausgabe
table = w.node(
    "Data Table", "Orange.widgets.data.owtable.OWTable", "(1180, 520)",
    props="{'auto_commit': True, '__version__': 1}",
)
w.link(select_node, table)

save = w.node(
    "Save Data", "Orange.widgets.data.owsave.OWSave", "(1180, 640)",
    props="{'auto_commit': True, '__version__': 1}",
)
w.link(select_node, save)


def build(w):
    lines = ["<?xml version='1.0' encoding='utf-8'?>"]
    lines.append(
        '<scheme version="2.0" '
        'title="Tomaten NIR Brix Analyse" '
        'description="Analyse der T4-T5 Tomaten-NIR-Daten: Datenvorbereitung, '
        'Qualitaet, PCA/PLS/Clustering, Neuronale Netze, XAI, FAISS. '
        'Daten: tomato_nir_brix.tab (im gleichen Ordner).">'
    )
    lines.append("\t<nodes>")
    for nid, name, qname, pos, title in w.nodes:
        lines.append(
            f'\t\t<node id="{nid}" name="{escape(name)}" qualified_name="{qname}" '
            f'project_name="Orange3" version="" title="{escape(title)}" position="{pos}" />'
        )
    lines.append("\t</nodes>")
    lines.append("\t<links>")
    for lid, src, dst, sch, dch, sid, did in w.links:
        lines.append(
            f'\t\t<link id="{lid}" source_node_id="{src}" sink_node_id="{dst}" '
            f'source_channel="{sch}" sink_channel="{dch}" enabled="true" '
            f'source_channel_id="{sid}" sink_channel_id="{did}" />'
        )
    lines.append("\t</links>")
    lines.append("\t<annotations>")
    lines.append(
        '\t\t<text id="0" type="text/plain" rect="(60.0, -40.0, 300.0, 50.0)" '
        'font-family="Helvetica" font-size="12">1. File laedt tomato_nir_brix.tab '
        "(bereinigt: 2014 Messungen, Brix=Ziel). Preprocess standardisiert, "
        'Select Columns setzt die 18 Kanaele als Features.</text>'
    )
    lines.append(
        '\t\t<text id="1" type="text/plain" rect="(40.0, 380.0, 300.0, 40.0)" '
        'font-family="Helvetica" font-size="12">Python Script (Qualitaet) prueft '
        "Rauschen, Drift und SNR und gibt den Ampel-Score aus.</text>"
    )
    lines.append(
        '\t\t<text id="2" type="text/plain" rect="(700.0, 450.0, 300.0, 40.0)" '
        'font-family="Helvetica" font-size="12">Test and Score vergleicht PLS (9 '
        "Komp.), MLP und Lineare Regression per Kreuzvalidierung (5 Folds).</text>"
    )
    lines.append("\t</annotations>")
    lines.append("\t<thumbnail />")
    lines.append("\t<node_properties>")
    for nid, fmt, data in w.props:
        lines.append(
            f'\t\t<properties node_id="{nid}" format="{fmt}">{data}</properties>'
        )
    lines.append("\t</node_properties>")
    lines.append("</scheme>")
    return "\n".join(lines)


with open(OUT, "w", encoding="utf-8") as f:
    f.write(build(w))
print(f"OK: {OUT}")
print(f"Nodes: {len(w.nodes)}, Links: {len(w.links)}")
