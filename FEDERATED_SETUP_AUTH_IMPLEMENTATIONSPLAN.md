# Implementationsplan: Federated Learning setup-fähig + DSGVO-konforme Anmeldung (NIR-IP)

Branch (Umsetzung): `vibe/fl-setup-auth-ausbau-<id>` — gemäß AGENTS.md nach Freigabe
Status: PLAN — Umsetzung erfolgt OP für OP nach Head-of-Development-Freigabe
Version: 2.0 — erstellt gemäß `AGENT_FRAMEWORK_INIT_PROMPT.md`, `MISSION_STATEMENT.md`,
`REPOSITORY_ALIGNMENT_AND_ROADMAP.md` (S9/FL1–FL6 erledigt) und Startsequenz (`TASK.md`).

---

## 1. Ist-Stand (Analyse 2026-10-15)

### 1.1 Federated Learning — vorhanden und getestet

| Baustein | Datei | Stand |
|---|---|---|
| FL-Kern (transport-agnostisch) | `services/federated_learning_service.py` | FedAvg/FedProx, non-IID-Sharding, PrivacyAuditor — ✅ S9 |
| Flower-Transport (echt) | `scripts/flower_superlink_entry.py` + `flower_supernode_entry.py` | ✅ FL6: Superlink + Supernode im Compose-Netz (9092), NirFlwrClient mit FL1-Ridge-Semantik |
| Föderierte Kalibration | `services/federated_calibration.py` | ✅ FL2: echte Modelle (PLS/MLP) statt nur Ridge |
| Privacy | `services/federated_privacy.py` | ✅ FL3: DP (ε-Budget) + SecAgg-Prüfung, ehrliche Degradation |
| UI/API | `django_project/api/federated_views.py`, `federated.html` | ✅ FL4: Consent-Gate (Opt-in, Default local_only), Runden-Dashboard |
| ILIAS-Kopplung | `services/federated_ilias_service.py`, `agents/ilias_course_agent.py` | ✅ FL5/FL6: Gruppen-Sessions, Status-Sync, ehrlicher degraded-Modus |
| Compose | `flower_server` + `flower_client` Services, Group `sparkfun_triad` | ✅ läuft im nir_network |
| Tests | FL1–FL6 + S9 + OP58-Matrizen | ✅ alle grün in CI |

**Was FEHLT für „setup-fähig" (vom Anwender aufbaubar):**

1. **Kein Onboarding-Weg:** Ein neuer Standort/Client kann dem Födersystem nicht beitreten — `flower_client` ist ein fester Compose-Service mit hartcodierter Gruppe (`FLOWER_CLIENT_GROUP=sparkfun_triad`), kein Registrierungs-/Beitrittsprozess.
2. **Kein Dateneingang am Client:** `FLOWER_CLIENT_DATA` (.npz) muss manuell vorhanden sein; es gibt keinen Weg, Trainingsdaten aus der eigenen Spektrendatenbank in ein Client-Shard zu überführen.
3. **Consent ist flüchtig:** `_consent_given` ist eine **globale Variable im Prozessspeicher** (`federated_views.py:27`) — Neustart = Einwilligung weg, nicht DSGVO-aufzeichnungspflichtig (Art. 7 Abs. 1 DSGVO: Nachweisbarkeit der Einwilligung).
4. **Keine Teilnehmer-/Standortverwaltung:** Wer nimmt gerade teil? Welche Gruppe? Keine Persistenz, nur Compose-Env.

### 1.2 Auth — Teilweise vorhanden, drei kritische Lücken

| Baustein | Stand | Lücke |
|---|---|---|
| JWT-Anmeldung | ✅ `djangorestframework-simplejwt`, `/api/token/` + Refresh | — |
| **Passwort-Wechsel** | ⚠️ UI **existiert komplett** (`settings.html`: Modal + `changePassword()` + `updatePassword()` → POST `/api/users/change_password/`) | **Der Endpoint existiert NICHT** — `change_password` kommt in keiner urls.py/View vor. Der Button scheitert still (404). Vermutlich Rest einer früheren Implementierung (AUTHENTICATION_GUIDE.md). |
| **2FA** | ❌ Nicht im Code (kein pyotp/TOTP, kein django-otp) | Ganz fehlend |
| **DSGVO-Anmeldung** | ⚠️ Teile: `PRIVACY_POLICY_URL` Setting (Default `/privacy/`), federated consent-Gate | Keine persistente Einwilligungs-Historie, keine Datums-/Text-Version-Erfassung, keine accountbezogene Nachweisbarkeit |

---

## 2. Zielbild

1. **FL setup-fähig:** Ein neuer Standort (z. B. zweites Praktikums-Labor) kann per dokumentiertem Weg dem Födersystem beitreten: Gruppe wählen, Trainingsdaten aus der eigenen DB als Shard bereitstellen, Supernode starten — alles ohne Code-Änderung, nur Konfiguration/CLI.
2. **DSGVO-konform:** Anmelde-/Registrierungsprozess mit dokumentierter Datenschutzerklärung, persistenter, revisionierbarer Einwilligung (wer, wann, welche Version, widerrufbar) — auch für die FL-Teilnahme separat.
3. **2FA:** TOTP-basiert (Authenticator-App), Opt-in pro Nutzer mit Wiederherstellungscodes.
4. **Passwort-Wechsel:** Der vorhandene UI-Dialog wird an einen echten, getesteten Endpoint angebunden (altes Passwort prüfen,Validatoren, alle Sessions invalidieren außer der aktuellen).

Verbindliche FL-Grundregeln bleiben: Rohdaten verlassen den Client nie, nur Modellparameter; Föderation ist Opt-in; keine öffentlichen Endpunkte (nur nir_network/loopback).

---

## 3. Geplante OPs

### FA1 — Passwort-Wechsel-Endpoint (kleinster Schritt zuerst)
- `django_project/api/views.py`: `ChangePasswordView(APIView)`: POST mit `current_password`/`new_password`, prüft aktuelles Passwort (`check_password`), Validatoren (`AUTH_PASSWORD_VALIDATORS`), `set_password`, invalidiert Refresh-Tokens (simplejwt `BlacklistMixin`/`outstanding_token`-Purge), Response im vom JS erwarteten Format (`success: true`).
- Route `api/users/change_password/` in `nir_web/urls.py` (passend zum vorhandenen JS-POST).
- UI: nur Feinschliff falls nötig (Modal existiert), Erfolgsfall logged out andere Sessions.
- Testmatrix: `tests/test_fa1_password_change.py` (falsches altes Passwort, schwaches neues, Erfolg + Token-Invalidierung).

### FA2 — Persistenter Consent + DSGVO-Einwilligungsprotokoll
- Neues Model `ConsentRecord` (`core/models.py`): user, Typ (`privacy_policy`, `federated_learning`), Version/Hash des Textes, Zeitpunkt, Ablauf (FL-Einwilligung befristet, Art. 7 Abs. 3 DSGVO), Widerrufszeitpunkt.
- Registrierung/Login: erstmalige Anmeldung erfordert Bestätigung der aktuellen Datenschutzerklärung (Version aus `settings.PRIVACY_POLICY_VERSION`, Text-Datei versioniert im Repo); ohne Einwilligung: nur Profil-Verwaltung, keine Analysen (Middleware-Gate, ehrlich, nirgends still).
- `federated_views.federated_consent`: schreibt `ConsentRecord` statt globale Variable; `_session_status` liest daraus (neuester, nicht widerrufener).
- Widerruf: `POST /api/federated/consent/ {"consent": false}` setzt Widerruf; laufende FL-Session stoppt ehrlich.
- Testmatrix: `tests/test_fa2_consent.py` (Erteilung, Widerruf, Ablauf, Nachweis-Historie).

### FA3 — TOTP-2FA (Opt-in)
- Abhängigkeit: `pyotp` (permissiv, MIT) — Anti-Code-Creep geprüft: für 2FA unvermeidbar, keine Eigenbau-Krypto.
- Model `TwoFactorConfig` (user, secret, bestätigt, Notfall-Codes als Hash).
- API: `POST /api/users/2fa/setup/` (liefert Secret + otpauth-URI/QR-Daten), `POST /api/users/2fa/verify/` (bestätigt + Notfall-Codes), `POST /api/users/2fa/disable/` (Passwort + TOTP nötig).
- Login-Flow: nach korrektem Passwort, wenn 2FA aktiv → 401 mit `{"mfa_required": true}` + temporäres Token → `POST /api/token/ {"mfa_token": ...}` (simplejwt-Claim-Erweiterung oder zweistufiger Login-View).
- UI: Settings-Seite Abschnitt „Zwei-Faktor-Authentifizierung" (QR, Verify, Notfall-Codes einmalig anzeigen).
- Testmatrix: `tests/test_fa3_2fa.py` (Setup, Verify, Login mit/ohne TOTP, Notfall-Code, Disable).

### FA4 — FL-Onboarding: Standort/Gruppe registrieren, Daten-Shard bauen
- Management-Command `manage.py fl_join <gruppe>`: prüft Consent (FA2), erzeugt/baut `FLOWER_CLIENT_DATA`-Shard aus der eigenen Spektrendatenbank (`SpectrumRecord`, Sharding nach `instrument_type`/`sample_type` wie FL2), schreibt Konfiguration (Gruppe, Superlink-Adresse aus Env).
- Compose-Templating: `flower_client`-Service auf `${FLOWER_CLIENT_GROUP}` und Datenvolume parametrisiert (Env statt hartcodiert); `docker-compose.override.yml.example` für eigene Standorte.
- UI: `federated.html` Abschnitt „Diesen Standort einbringen" — Gruppe wählen, Shard-Vorschau (Anzahl Spektren je Shard, Provenance), Status des lokalen Supernode.
- Doku: `docs/FL_SETUP.md` — Standort-Beitritt in 5 Schritten.
- Testmatrix: `tests/test_fa4_fl_join.py` (Shard-Bau aus DB, non-IID-Aufteilung, Consent-Gate).

### FA5 — Teilnehmer-Verwaltung + Status-Sichtbarkeit
- Model `FederationParticipant` (Gruppe, Standort-Label, ultimo Join, Status, letzter Rundenbeitrag).
- Flower-Runden-Hook → Teilnehmer-Status aktualisieren (aus FL4-Runden-Historie).
- UI: `federated.html` Standort-Tabelle (Gruppe, Status, letzte Aktivität, beigetragen Runden); Admin-Übersicht.
- Testmatrix: `tests/test_fa5_participants.py`.

### FA6 — ILIAS: FL-Gruppen im Kurs-Kontext (FL5-Ausbau)
- Föderierte Gruppe ↔ ILIAS-Kursgruppe verknüpfen (FL5-Service erweitern); Status des FL-Trainings in den Kurs syncen.
- Ehrliche Degradation ohne OAuth2 (bestehender OP2-Vertrag).
- Testmatrix: `tests/test_fa6_ilias_federation.py`.

**Reihenfolge:** FA1 → FA2 → FA3 (parallel zu FA4 möglich) → FA4 → FA5 → FA6.
FA1/FA2 sind die DSGVO-relevanten Grundlagen und gehen zuerst.

---

## 4. Nicht-Ziele / Out of Scope

- Keine öffentlichen FL-Endpunkte (nur nir_network-intern; Sandbox-/Hostgrenze unverändert).
- Keine neuen Abhängigkeiten außer `pyotp` (FA3) — geprüft gegen die Lizenz-Regeln (MIT).
- Keine Änderungen an `nir_platform/`, `HANDHELD/`, `framework/`, `paperless-mistral-setup/` (archiviert).
- Weaviate bleibt out of scope; Qdrant unverändert.
- Kein Eigenbau von Krypto-Primitiven (2FA via pyotp, Sessions via simplejwt).

## 5. Definition of Done (pro OP)

- Testmatrix grün in CI (neue Zeile in der CI-Run-Liste), Regressionen FL1–FL6/S9 grün.
- `manage.py check` ohne Befunde; ROADMAP-Update (neuer Abschnitt FA1–FA6) + TASK.md-Eintrag.
- Doku aktualisiert (AUTHENTICATION_GUIDE.md für FA1–FA3, FL_SETUP.md für FA4+).
