# Handbuch zur Nutzung von Napari für die Analyse von Spektraldaten

## Einleitung

Napari ist eine Open-Source-Plattform für die wissenschaftliche Bildverarbeitung, die sich durch ihre Flexibilität und Erweiterbarkeit auszeichnet. Dieses Handbuch empfiehlt Napari als Werkzeug zur Analyse von Spektraldaten, wie sie von einem DIY Matchbox-Spektrometer geliefert werden. Napari eignet sich besonders für die Visualisierung, Bearbeitung und Auswertung von hyperspektralen Daten, die in Form von Bildwürfeln (Image Cubes) vorliegen.

---

## 1. Installation und Einrichtung

### 1.1 Voraussetzungen

- Python 3.9 oder höher
- pip (Python-Paketmanager)
- Empfohlen: Virtuelle Umgebung (z. B. `venv` oder `conda`)

### 1.2 Installation von Napari

Napari kann über pip installiert werden:

```bash
pip install napari
```

Für die Arbeit mit Spektraldaten werden zusätzliche Plugins benötigt. Installieren Sie diese mit:

```bash
pip install napari-plugin-engine
pip install napari-spectral
```

### 1.3 Installation spezifischer Plugins für Spektraldaten

Für die Analyse von Spektraldaten werden folgende Plugins empfohlen:

- **napari-spectral**: Ermöglicht die Visualisierung und Analyse von hyperspektralen Daten.
- **napari-plot-profile**: zur Erstellung von Profilen und Spektren.
- **napari-skimage-regionprops**: zur Segmentierung und Analyse von Regionen.

Installation:

```bash
pip install napari-spectral napari-plot-profile napari-skimage-regionprops
```

### 1.4 Starten von Napari

Napari kann über die Kommandozeile gestartet werden:

```bash
napari
```

Alternativ kann Napari auch aus einem Python-Skript heraus gestartet werden:

```python
import napari
napari.run()
```

---

## 2. Datenimport und Vorbereitung

### 2.1 Datenformat des DIY Matchbox-Spektrometers

Ein DIY Matchbox-Spektrometer liefert typischerweise Spektraldaten in folgenden Formaten:

- **CSV-Dateien**: Enthalten Wellenlängen und zugehörige Intensitätswerte.
- **Bilddateien**: Hyperspektrale Würfel als mehrdimensionale Arrays (z. B. `.npy`, `.tif`).
- **Textdateien**: Rohdaten, die in ein lesbares Format umgewandelt werden müssen.

### 2.2 Import von Spektraldaten in Napari

#### Option 1: Import von Bildwürfeln (Image Cubes)

1. Öffnen Sie Napari.
2. Klicken Sie auf **File > Open** oder ziehen Sie die Datei per Drag & Drop in den Viewer.
3. Unterstützte Formate: `.tif`, `.npy`, `.hdf5`.

#### Option 2: Import von CSV-Daten

1. Konvertieren Sie die CSV-Datei in ein für Napari lesbares Format (z. B. `.npy`).
   Beispiel mit Python:
   ```python
   import numpy as np
   import pandas as pd
   
   # CSV-Datei einlesen
   data = pd.read_csv('spektren.csv')
   
   # In ein 3D-Array umwandeln (Beispiel: 100x100x256 für 100x100 Pixel und 256 Wellenlängen)
   spectral_cube = np.random.rand(100, 100, 256)  # Ersetzen Sie dies durch Ihre Daten
   
   # Speichern als .npy-Datei
   np.save('spectral_cube.npy', spectral_cube)
   ```
2. Laden Sie die `.npy`-Datei in Napari.

#### Option 3: Direkter Import über Python-Skript

```python
import napari
import numpy as np

# Spektraldaten laden (Beispiel: 100x100x256)
data = np.load('spektren.npy')

# Napari-Viewer starten
viewer = napari.Viewer()
viewer.add_image(data, name='Spektralwürfel')

napari.run()
```

---

## 3. Visualisierung von Spektraldaten

### 3.1 Grundlegende Visualisierung

1. Nach dem Import wird der Spektralwürfel als 3D-Datensatz angezeigt.
2. Nutzen Sie die **Layer Controls** (rechts im Fenster), um die Darstellung anzupassen:
   - **Colormap**: Wählen Sie eine Farbskala (z. B. `viridis`, `inferno`).
   - **Contrast**: Passen Sie die Helligkeit und den Kontrast an.
   - **Opacity**: Regulieren Sie die Transparenz.

### 3.2 Verwendung des napari-spectral Plugins

1. Installieren Sie das Plugin (falls noch nicht geschehen, siehe Abschnitt 1.3).
2. Öffnen Sie den Spektralwürfel in Napari.
3. Nutzen Sie die Werkzeuge des Plugins:
   - **Spectrum Viewer**: Zeigt das Spektrum für einen ausgewählten Pixel an.
   - **Wavelength Slider**: Ermöglicht das Durchblättern der Wellenlängen.
   - **Band Selection**: Wählen Sie einzelne spektrale Bänder zur Analyse aus.

#### Beispiel: Spektrum eines Pixels anzeigen

1. Klicken Sie auf einen Pixel im Spektralwürfel.
2. Öffnen Sie den **Spectrum Viewer** (über das Plugin-Menü oder die Symbolleiste).
3. Das Spektrum für den ausgewählten Pixel wird angezeigt.

### 3.3 Erstellen von Spektralprofilen

Mit dem **napari-plot-profile** Plugin können Sie Spektralprofile erstellen:

1. Wählen Sie einen Bereich (z. B. eine Linie oder ein Rechteck) im Spektralwürfel aus.
2. Öffnen Sie das **Plot Profile** Werkzeug.
3. Das Plugin zeigt die Intensitätswerte entlang der ausgewählten Linie oder Region an.

---

## 4. Datenanalyse

### 4.1 Spektrale Merkmale extrahieren

#### Absorptionsbanden identifizieren

1. Nutzen Sie den **Spectrum Viewer**, um Spektren zu analysieren.
2. Suchen Sie nach typischen Absorptionsbanden (z. B. bei 670 nm für Chlorophyll).
3. Markieren Sie die Wellenlängenbereiche mit niedriger Intensität.

#### Beispiel: Absorptionsbande bei 670 nm

- Wählen Sie einen Pixel mit bekannter Vegetation aus.
- Analysieren Sie das Spektrum im **Spectrum Viewer**.
- Identifizieren Sie die Absorptionsbande bei ~670 nm (Chlorophyll-Absorption).

### 4.2 Spektrale Indizes berechnen

Spektrale Indizes wie der **NDVI (Normalized Difference Vegetation Index)** können direkt in Napari berechnet werden:

1. Verwenden Sie ein Python-Skript, um den Index zu berechnen:
   ```python
   import numpy as np
   
   # Beispiel: NDVI berechnen (Band 80 = NIR, Band 40 = Rot)
   band_nir = data[:, :, 80]  # Nahinfrarot-Band
   band_red = data[:, :, 40]  # Rotes Band
   
   ndvi = (band_nir - band_red) / (band_nir + band_red)
   
   # NDVI in Napari anzeigen
   viewer.add_image(ndvi, name='NDVI')
   ```

2. Fügen Sie das Ergebnis als neue Ebene in Napari hinzu.

### 4.3 Klassifizierung von Spektraldaten

Für die Klassifizierung von Spektraldaten können Sie:

- **Manuelle Klassifizierung**: Nutzen Sie die Segmentierungswerkzeuge von Napari, um Regionen zu markieren.
- **Automatische Klassifizierung**: Verwenden Sie Maschinenlernmethoden (z. B. `scikit-learn`).

#### Beispiel: Einfache Klassifizierung mit scikit-learn

```python
from sklearn.cluster import KMeans
import numpy as np

# Daten vorbereiten (Beispiel: 10000 Pixel, 256 Bänder)
pixels = data.reshape(-1, 256)

# K-Means Klassifizierung
kmeans = KMeans(n_clusters=3)
labels = kmeans.fit_predict(pixels)

# Labels in die ursprüngliche Form zurückbringen
labels = labels.reshape(data.shape[:2])

# In Napari anzeigen
viewer.add_labels(labels, name='Klassifizierung')
```

---

## 5. Export der Ergebnisse

### 5.1 Export von Bildern

1. Klicken Sie mit der rechten Maustaste auf die Ebene, die Sie exportieren möchten.
2. Wählen Sie **Save Layer As**.
3. Wählen Sie das gewünschte Format (z. B. `.tif`, `.png`).

### 5.2 Export von Spektraldaten

#### Export als CSV

```python
import pandas as pd

# Spektrum eines Pixels exportieren
pixel_spectrum = data[50, 50, :]  # Beispiel: Pixel bei (50, 50)
wavelengths = np.arange(400, 700, 1)  # Beispiel: Wellenlängen von 400-700 nm

# In DataFrame umwandeln
df = pd.DataFrame({
    'Wellenlänge (nm)': wavelengths,
    'Intensität': pixel_spectrum
})

# Als CSV speichern
df.to_csv('pixel_spectrum.csv', index=False)
```

#### Export als .npy

```python
# Spektralwürfel exportieren
np.save('spectral_cube_processed.npy', data)
```

---

## 6. Tipps und Tricks

### 6.1 Performance-Optimierung

- **Daten reduzieren**: Arbeiten Sie mit Ausschnitten der Daten, um die Performance zu verbessern.
  ```python
  # Ausschnitt der Daten laden
  subset = data[10:50, 10:50, :]
  viewer.add_image(subset, name='Ausschnitt')
  ```

- **Downsampling**: Reduzieren Sie die Auflösung der Daten.
  ```python
  from skimage.transform import resize
  
  # Daten herunterskalieren
  downsampled = resize(data, (data.shape[0]//2, data.shape[1]//2, data.shape[2]))
  viewer.add_image(downsampled, name='Herunterskaliert')
  ```

### 6.2 Nützliche Plugins

| Plugin | Zweck |
|--------|-------|
| napari-spectral | Visualisierung und Analyse von hyperspektralen Daten |
| napari-plot-profile | Erstellen von Profilen und Spektren |
| napari-skimage-regionprops | Segmentierung und Analyse von Regionen |
| napari-segment-blobs | Automatische Segmentierung von Objekten |
| napari-animation | Erstellen von Animationen aus Spektraldaten |

### 6.3 Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| Daten werden nicht geladen | Überprüfen Sie das Dateiformat. Konvertieren Sie ggf. in `.npy` oder `.tif`. |
| Langsame Performance | Reduzieren Sie die Datengröße oder verwenden Sie Ausschnitte. |
| Plugin funktioniert nicht | Überprüfen Sie die Installation: `pip install --upgrade <plugin-name>`. |
| Spektrum wird nicht angezeigt | Stellen Sie sicher, dass der Spektralwürfel korrekt geladen wurde. |

---

## 7. Beispiel-Workflow

### Schritt-für-Schritt-Anleitung: Analyse eines Spektralwürfels

1. **Daten laden**
   - Speichern Sie die Daten des Matchbox-Spektrometers als `.npy`-Datei.
   - Laden Sie die Datei in Napari.

2. **Daten visualisieren**
   - Passen Sie Colormap und Kontrast an.
   - Nutzen Sie den **Wavelength Slider**, um durch die Wellenlängen zu blättern.

3. **Spektrum analysieren**
   - Wählen Sie einen Pixel aus und öffnen Sie den **Spectrum Viewer**.
   - Identifizieren Sie Absorptionsbanden.

4. **Spektrale Indizes berechnen**
   - Berechnen Sie z. B. den NDVI (siehe Abschnitt 4.2).
   - Fügen Sie das Ergebnis als neue Ebene hinzu.

5. **Klassifizierung durchführen**
   - Segmentieren Sie die Daten manuell oder mit K-Means.
   - Visualisieren Sie die Klassifizierungsergebnisse.

6. **Ergebnisse exportieren**
   - Exportieren Sie die bearbeiteten Daten als `.tif` oder `.npy`.
   - Exportieren Sie Spektren als CSV.

---

## 8. Ressourcen und Weiterführende Links

- [Napari Offizielle Dokumentation](https://napari.org/stable/)
- [napari-spectral Plugin](https://github.com/napari/napari-spectral)
- [napari-plot-profile Plugin](https://github.com/napari/napari-plot-profile)
- [DIY Matchbox-Spektrometer (Public Lab)](https://publiclab.org/wiki/matchbox-spectrometer)
- [Scikit-learn für Klassifizierung](https://scikit-learn.org/stable/)

---

## 9. Glossar

| Begriff | Erklärung |
|---------|-----------|
| **Hyperspektral** | Daten mit vielen spektralen Bändern (typischerweise > 100). |
| **Spektralwürfel** | 3D-Datensatz mit räumlichen (x, y) und spektralen (λ) Dimensionen. |
| **Absorptionsbande** | Wellenlängenbereich, in dem Licht absorbiert wird (z. B. durch Chlorophyll). |
| **NDVI** | Normalized Difference Vegetation Index, ein Maß für Vegetationsdichte. |
| **Pixel-Spektrum** | Spektrum eines einzelnen Pixels im Spektralwürfel. |

---

## 10. Anhang: Python-Skript für den Komplett-Workflow

```python
import napari
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

# 1. Daten laden (Beispiel: 100x100x256)
data = np.load('spektren.npy')

# 2. Napari-Viewer starten
viewer = napari.Viewer()
viewer.add_image(data, name='Spektralwürfel')

# 3. NDVI berechnen (Band 80 = NIR, Band 40 = Rot)
band_nir = data[:, :, 80]
band_red = data[:, :, 40]
ndvi = (band_nir - band_red) / (band_nir + band_red)
viewer.add_image(ndvi, name='NDVI')

# 4. Klassifizierung mit K-Means
pixels = data.reshape(-1, 256)
kmeans = KMeans(n_clusters=3)
labels = kmeans.fit_predict(pixels)
labels = labels.reshape(data.shape[:2])
viewer.add_labels(labels, name='Klassifizierung')

# 5. Spektrum eines Pixels exportieren
pixel_spectrum = data[50, 50, :]
wavelengths = np.arange(400, 700, 1)
df = pd.DataFrame({
    'Wellenlänge (nm)': wavelengths,
    'Intensität': pixel_spectrum
})
df.to_csv('pixel_spectrum.csv', index=False)

# Napari starten
napari.run()
```

---

*Handbuch erstellt für die Nutzung von Napari zur Analyse von Spektraldaten eines DIY Matchbox-Spektrometers.*