# ESP32-CAM Dokumenten-Scanner

Der ESP32-CAM fotografiert Dokumente und lädt sie **direkt** in Paperless hoch — ohne Bridge-Software. Der Datenfluss:

```
ESP32-CAM (Foto) 
   → POST /api/documents/post_document/ (multipart, TOKEN-Auth)
   → Paperless-ngx Consume 
   → OCR (deu) 
   → paperless-ai (Mistral via Ollama) verschlagwortet automatisch
   → Ablage nach Regeln
```

## Warum die REST-API statt eines Netzwerk-Ordners?

Der ESP32 hat keinen Einfluss darauf, was Paperless mit dem Bild macht — das OCR und die Verschlagwortung passieren ohnehin in Paperless (JPEG wird automatisch OCR-gelesen, per `PAPERLESS_OCR_LANGUAGE: deu`). Der direkte API-Upload hat aber Vorteile:

- kein NFS/SMB-Mount auf dem ESP32 nötig
- Upload bestätigt die Entgegennahme direkt (HTTP 200)
- pro ESP32 eigener API-Token möglich (Audit/Tracking)

Der consume-Ordner des Docker-Setups funktioniert natürlich weiterhin parallel (z. B. vom PC aus).

## Vorbereitung

1. **API-Token erzeugen:** Paperless-Weboberfläche → Einstellungen → API Auth → Token erstellen. Diesen Token (plus Server-IP) in den Sketch eintragen.

2. **Arduino IDE einrichten:**
   - Datei → Einstellungen → zusätzliche Boardverwalter-URL: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - Boardsverwalter: "esp32 by Espressif Systems" installieren
   - Board: "AI Thinker ESP32-CAM"

3. **Sketch anpassen** (`=== KONFIGURATION ===`):
   - WLAN-SSID/Passwort
   - `PAPERLESS_HOST` = IP deines Servers (z. B. `192.168.1.50`)
   - `PAPERLESS_TOKEN` = API-Token
   - ggf. `FRAME_SIZE` (XGA ist ein guter Standard für A4-Dokumente)

4. **Upload:** Sketch → Hochladen. Beim ESP32-CAM: GPIO0 mit GND verbinden für den Flash-Modus, danach trennen und Reset.

## Auslöser — drei Varianten

### Variante A: Panic-Button (im Sketch enthalten)
Der Boot-Button auf dem Board (GPIO0) ist bereits als Auslöser verdrahtet (`BUTTON_PIN 0`). Drücken = Foto + Upload. LED-Signale:
- rote LED kurz an während Aufnahme/Upload
- 3× langsames Blinken = Upload fehlgeschlagen (WLAN/Server prüfen)
- 5× schnelles Blinken = Kamerafehler
- weiße Blitz-LED kurz an = Erfolg

### Variante B: externer Taster (empfohlen fürs Gehäuse)
Beliebiger Momentary-Button zwischen **GPIO12** und **GND**; dann im Sketch `BUTTON_PIN 12` setzen (GPIO0 als Auslöser ist praktisch, blockiert aber den Flash-Modus). `INPUT_PULLUP` ist im Sketch aktiv, ein Vorwiderstand ist nicht nötig.

### Variante C: automatisch per Zeitintervall
`AUTO_INTERVAL_S` im Sketch auf z. B. `60` setzen → alle 60 s ein Foto. Nützlich für Stapel-Scans: Dokument unter die Kamera legen, Kamera fotografiert durch. **Nachteil:** leere Bilder, wenn kein Dokument liegt — deswegen ist der Button-Modus der bessere Standard.

**Vorschlag fürs Setup:** Variante B (externer Taster am Gehäuse, GPIO12) — der Boot-Button bleibt für Flashen/Konfiguration frei, und du lörst gezielt pro Dokument aus. 

## Gehäuse-/Positionierungstipps

- Die OV2640 ist ein Weitwinkel; für A4 mindestens **~25–30 cm Abstand**, Doc gerade ausrichten
- Für scharfe Textbilder besser **SVGA/XGA + gute Beleuchtung** als UXGA + Bildrauschen; zwei seitliche LED-Panels (gleichmäßig, ohne Reflexe) geben das beste OCR-Ergebnis
- Fokus der OV2640-Module ist oft auf ~30 cm fixiert (manuell drehbar) — vor dem Einbau justieren
- Statt Infrarot-Blitz: konstante Beleuchtung, Blitz-LED erzeugt Reflexe auf glattem Papier

## Troubleshooting

- **Upload schlägt fehl:** Token/Server-IP prüfen; `docker compose logs -f paperless` zeigt, ob die Anfrage ankommt.
- **Bild unscharf:** Fokus nachjustieren; Auflösung reduzieren; Licht verbessern.
- **Kein PSRAM-Fehler:** Bei Boards ohne PSRAM `cfg.fb_location = CAMERA_DRAM_FB` und `FRAME_SIZE` auf SVGA reduzieren.
- **ESP32 bootet nicht nach Upload:** GPIO0 war beim Reset noch mit GND verbunden — Verbindung trennen, Reset drücken.

## Erweiterungsideen

- Deep-Sleep + Button-Interrupt (Wake-on-Button) für Batteriebetrieb
- Web-UI auf dem ESP32 (AP-Modus) zur Live-Vorschau vor dem Auslösen (Example `CameraWebServer` als Basis)
- Bildvorverarbeitung direkt auf dem ESP32 (Graustufen, Kontrast) — in den meisten Fällen unnötig, die Paperless-OCR ist robust
