/*
 * ESP32-CAM Dokumenten-Scanner
 * -----------------------------
 * Fotografiert ein Dokument und lädt das JPEG direkt über die
 * Paperless-ngx REST-API in den Consume-Ordner hoch.
 *
 * Hardware:
 *   - ESP32-CAM (AI-Thinker) mit OV2640
 *   - optional: Panic-Button /(GPIO0), LED rot (GPIO33), LED grün (GPIO4/Blitz-LED)
 *
 * Bibliotheken (Bibliotheksverwalter):
 *   - "ESP32" Boardunterstützung (Boardsverwalter, URL siehe README)
 *   - keine weiteren Libraries nötig
 *
 * Konfiguration siehe "=== KONFIGURATION ===" unten.
 */

#include "esp_http_client.h"
#include "esp_camera.h"
#include <WiFi.h>

// ==================== KONFIGURATION ====================
const char* WIFI_SSID     = "DEIN_WLAN";
const char* WIFI_PASSWORD = "DEIN_PASSWORT";

// Paperless-ngx API (Port 8000 wie im docker-compose-Setup)
const char* PAPERLESS_HOST  = "192.168.1.50";
const int   PAPERLESS_PORT  = 8000;
const char* PAPERLESS_TOKEN = "DEIN_PAPERLESS_API_TOKEN";

// Pins (AI-Thinker ESP32-CAM)
#define BUTTON_PIN     0   // Boot-Button am Board (Panic-Button)
#define LED_STATUS    33  // rote Onboard-LED (aktiv LOW)
#define LED_OK        4   // Blitz-LED (kann als Erfolgs-LED dienen)

// Auflösung: FRAMESIZE_UXGA(1600x1200) / SXGA / XGA(1024x768) / SVGA(800x600)
framesize_t FRAME_SIZE  = FRAMESIZE_XGA;
int JPEG_QUALITY        = 12;   // 10-14 gut für Dokumente (niedriger = besser)

// Automatischer Modus: alle X Sekunden ein Bild (0 = aus, nur Button)
uint32_t AUTO_INTERVAL_S = 0;
// ======================================================

WiFiClient client;
uint8_t* jpgBuf = nullptr;
size_t   jpgLen = 0;
uint32_t lastShotMs = 0;

// --- Kamera-Pins für AI-Thinker ESP32-CAM ---
#define PWDN_GPIO_NUM  32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM   0
#define SIOD_GPIO_NUM  26
#define SIOC_GPIO_NUM  27
#define Y9_GPIO_NUM    35
#define Y8_GPIO_NUM    34
#define Y7_GPIO_NUM    39
#define Y6_GPIO_NUM    36
#define Y5_GPIO_NUM    21
#define Y4_GPIO_NUM    19
#define Y3_GPIO_NUM    18
#define Y2_GPIO_NUM     5
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM  23
#define PCLK_GPIO_NUM  22

void blink(int pin, int times, int ms) {
  for (int i = 0; i < times; i++) { digitalWrite(pin, LOW); delay(ms); digitalWrite(pin, HIGH); delay(ms); }
}

bool initCamera() {
  camera_config_t cfg = {};
  cfg.ledc_channel = LEDC_CHANNEL_0;
  cfg.ledc_timer   = LEDC_TIMER_0;
  cfg.pin_sccb_sda = SIOD_GPIO_NUM;
  cfg.pin_sccb_scl = SIOC_GPIO_NUM;
  cfg.pin_pwdn     = PWDN_GPIO_NUM;
  cfg.pin_reset    = RESET_GPIO_NUM;
  cfg.pin_xclk     = XCLK_GPIO_NUM;
  cfg.pin_pclk     = PCLK_GPIO_NUM;
  cfg.pin_vsync    = VSYNC_GPIO_NUM;
  cfg.pin_href    = HREF_GPIO_NUM;
  cfg.pin_y2      = Y2_GPIO_NUM;
  cfg.pin_y3      = Y3_GPIO_NUM;
  cfg.pin_y4      = Y4_GPIO_NUM;
  cfg.pin_y5      = Y5_GPIO_NUM;
  cfg.pin_y6      = Y6_GPIO_NUM;
  cfg.pin_y7      = Y7_GPIO_NUM;
  cfg.pin_y8      = Y8_GPIO_NUM;
  cfg.pin_y9      = Y9_GPIO_NUM;
  cfg.xclk_freq_hz = 20000000;
  cfg.frame_size   = FRAME_SIZE;
  cfg.pixel_format = PIXFORMAT_JPEG;
  cfg.jpeg_quality = JPEG_QUALITY;
  cfg.fb_count     = 1;
  cfg.fb_location  = CAMERA_PSRAM_FB;  // nutzt PSRAM, falls vorhanden

  return esp_camera_init(&cfg) == ESP_OK;
}

bool capture() {
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) return false;
  free(jpgBuf);
  jpgLen = fb->len;
  jpgBuf = (uint8_t*) malloc(jpgLen);
  memcpy(jpgBuf, fb->buf, jpgLen);
  esp_camera_fb_return(fb);
  return jpgBuf != nullptr;
}

bool uploadToPaperless() {
  // multipart/form-data POST an /api/documents/post_document/
  String host = String(PAPERLESS_HOST);
  String boundary = "----esp32cam" + String(micros(), HEX);

  String head = "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"document\"; filename=\"scan.jpg\"\r\n";
  head += "Content-Type: image/jpeg\r\n\r\n";

  String tail = "\r\n--" + boundary + "\r\n";
  tail += "Content-Disposition: form-data; name=\"stream\"\r\n\r\n";
  tail += "true\r\n";
  tail += "--" + boundary + "--\r\n";

  WiFiClient ws;
  if (!ws.connect(PAPERLESS_HOST, PAPERLESS_PORT)) return false;

  String req = "POST /api/documents/post_document/ HTTP/1.1\r\n";
  req += "Host: " + host + ":" + String(PAPERLESS_PORT) + "\r\n";
  req += "Authorization: TOKEN " + String(PAPERLESS_TOKEN) + "\r\n";
  req += "Content-Type: multipart/form-data; boundary=" + boundary + "\r\n";
  req += "Content-Length: " + String(head.length() + jpgLen + tail.length()) + "\r\n";
  req += "Connection: close\r\n\r\n";

  ws.print(req);
  ws.print(head);
  // JPEG in Chunks senden
  size_t sent = 0;
  while (sent < jpgLen) {
    size_t n = min((size_t)1024, jpgLen - sent);
    size_t w = ws.write(jpgBuf + sent, n);
    if (w == 0) { ws.stop(); return false; }
    sent += w;
  }
  ws.print(tail);

  // Antwort lesen
  bool ok = false;
  uint32_t start = millis();
  while (ws.connected() && millis() - start < 10000) {
    if (ws.available()) {
      String line = ws.readStringUntil('\n');
      if (line.startsWith("HTTP/1.1 200")) ok = true;
    }
  }
  ws.stop();
  return ok;
}

void shoot() {
  digitalWrite(LED_STATUS, LOW);  // an (rot, aktiv LOW)
  if (!capture()) { blink(LED_STATUS, 5, 100); return; }
  if (!uploadToPaperless()) { blink(LED_STATUS, 3, 300); return; }
  // Erfolg: kurz grün/weiß aufblitzen
  digitalWrite(LED_OK, HIGH); delay(200); digitalWrite(LED_OK, LOW);
  digitalWrite(LED_STATUS, HIGH);  // aus
}

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(LED_STATUS, OUTPUT);
  pinMode(LED_OK, OUTPUT);
  digitalWrite(LED_STATUS, HIGH);  // aus (aktiv LOW)
  digitalWrite(LED_OK, LOW);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_STATUS, LOW); delay(100); digitalWrite(LED_STATUS, HIGH); delay(400);
  }

  if (!initCamera()) {
    // Kamera fehlgeschlagen: dauerhaft blinken
    while (true) { blink(LED_STATUS, 10, 50); delay(500); }
  }
  digitalWrite(LED_STATUS, HIGH);
}

void loop() {
  // Button gedrückt (LOW-aktiv)?
  if (digitalRead(BUTTON_PIN) == LOW) {
    delay(50);  // entprellen
    if (digitalRead(BUTTON_PIN) == LOW) {
      shoot();
      // auf Loslassen warten, damit kein Doppel-Auslösen
      while (digitalRead(BUTTON_PIN) == LOW) delay(10);
    }
  }

  // optionaler Auto-Modus
  if (AUTO_INTERVAL_S > 0 && millis() - lastShotMs > AUTO_INTERVAL_S * 1000UL) {
    shoot();
    lastShotMs = millis();
  }
}
