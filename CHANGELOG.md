# Changelog

## 2026-04-26

### Kategorisierung und Regeln

- Konflikte in `src/category_rules.py` bereinigt:
  - doppelte Keys konsolidiert
  - PayPal/eBay-Konflikt entschärft
  - VISA/Mastercard als reine Rail-Trigger reduziert
  - zu generische Keywords entschärft
  - Kategorienamen konsolidiert
- `categorize_generic_provider()` erweitert (neue zielgerichtete Keywords, spezifisch vor allgemein).
- Provider-Routing verbessert: `purpose`/`booking_text` bleiben primaer, `counterparty` wird als Kontext genutzt.
- Mojibake-/Encoding-Artefakte fuer Matching in `src/data_cleaner.py` repariert.
- Empfaenger- und Reise-/Provider-spezifische Regeln nach manueller Analyse + Webrecherche ergänzt
  (u. a. Drillisch, Herrmann Exklusiv, Engbers, BavariaDirekt, BD24, DEURAG, Freizeitbad/Badegaerten).

### Pipeline / Daten

- Pipeline mehrfach neu ausgefuehrt (`src/run_pipeline.py`), `data/final_transactions.csv` aktualisiert.
- Ergebnis: `uncategorized` von urspruenglich deutlich hoeher auf nur noch wenige Restfaelle reduziert.
- Datenstruktur fuer Rohimporte eingefuehrt:
  - neue Eingangsablage `data/incoming/`
  - Loader priorisiert `data/incoming/` und faellt bei Bedarf auf `data/` zurueck.

### Dashboard (`app.py`)

- Diagramme visuell verbessert (Farbpalette, Hovertexte, bessere Beschriftungen).
- Zeitraumanzeige im Kopfbereich ergänzt.
- Kontostandverlauf aus `balance` ergänzt und Zahlenparsing (DE/EN) robust gemacht.
- `Sicherheit`-Spalte bei regelmaessigen Zahlungen korrekt als Prozent skaliert.
- Legende zur Bedeutung von `Sicherheit` ergänzt.
- Kategorie-UX verbessert:
  - Umschalter `Zusammengefasst` / `Detailliert`
  - lesbare Labels statt technischer Dot-Namen im Alltag
- Datumsfilter stabilisiert:
  - manueller Bereich priorisiert
  - ein gemeinsames Datumsbereich-Feld mit robustem Verhalten beim Start-/Ende-Setzen
  - Schnellwahl und manueller Bereich sauber synchronisiert (kein Blockieren der Schnellwahl mehr).
- Neuer CSV-Import im Dashboard:
  - Dateiauswahl direkt im UI
  - Speichern nach `data/incoming/`
  - Pipeline-Run aus dem UI
  - Cache-Reset und Reload nach erfolgreichem Import.

### Betrieb

- Streamlit-Instanzen bereinigt und neu gestartet, um Cache-/Altinstanz-Probleme auszuschliessen.

### Mehrprofil / Konten

- Mehrbenutzer-/Mehrkonto-Support in `app.py` ergänzt:
  - Profilauswahl (`Benutzer / Konto`)
  - neues Profil anlegen
  - Profil loeschen mit Sicherheits-Checkbox
  - hervorgehobene Anzeige des aktiven Profils
- Profilstruktur eingefuehrt:
  - `data/users/<profil>/incoming`
  - `data/users/<profil>/final_transactions.csv`
  - `outputs/users/<profil>/...`
- Einmalige Migration fuer bestaende:
  - bisheriges `default` wurde auf `mario` umgestellt
  - Legacy-Importe werden bei Bedarf ins Basiskonto uebernommen
- `src/run_pipeline.py` erweitert:
  - neue CLI-Parameter `--data-dir` und `--output-dir`
  - pipelinefaehige Verarbeitung je Profilkontext

### Zusätzliche Regelverfeinerungen (Profil-Reviews Mario/Juliane)

- Neue Kategorien:
  - `dining.school_meals` (Schul-/Kitaessen)
  - `personal.haircare` (Friseur)
- Neue/erweiterte Keywords u. a. fuer:
  - SFZ CoWerk, Lederwaren Boehm, Salon Schnittpunkt
  - Regionalverkehr Erzgebirge / Bildungsticket
  - TEDi, Maec-Geiz, KiK, IKEA
  - kinoheld, Repp Mediumtechnik
  - ROEBEN GAS
- Spezielle Prioritaetsmuster ergänzt:
  - `paypal.*kinoheld` -> `entertainment.hobby`
  - `roeben.*gas` -> `housing.utilities`
- Ergebnis der Nachschaerfung:
  - Juliane-Profil von ehemals vielen Restfaellen auf `uncategorized = 0`
  - Mario-spezifische Fehlzuordnungen (Kino/Gas) korrigiert.
