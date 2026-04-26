# XCash

Lokale Finanzanalyse fuer deutsche Kontoauszuege (CSV) mit Pipeline, Kategorisierung, Anomalie-Erkennung und Streamlit-Dashboard.

## Kernfunktionen

- CSV-Import und Normalisierung fuer Bankexporte (`src/data_loader.py`)
- Bereinigung, Deduplizierung und Kategorisierung (`src/data_cleaner.py`, `src/category_rules.py`)
- EDA + Kennzahlen (`src/eda.py`)
- Wiederkehrende Zahlungen (`src/recurring_detector.py`)
- Anomalie-Erkennung (`src/anomaly_detector.py`)
- Dashboard (`app.py`)

## Start

1. Abhaengigkeiten installieren:

```bash
pip install -r requirements.txt
```

2. Pipeline laufen lassen:

```bash
python src/run_pipeline.py
```

Optional profilbezogen:

```bash
python src/run_pipeline.py --data-dir data/users/mario --output-dir outputs/users/mario
```

3. Dashboard starten:

```bash
streamlit run app.py --server.headless true --browser.gatherUsageStats false --server.port 8501
```

## Wichtige Datenpfade

- Profilordner fuer Konten: `data/users/<profil>/`
- Profil-Rohimporte (manuell oder UI-Upload): `data/users/<profil>/incoming/`
- Profil-Verarbeitungsdaten: `data/users/<profil>/final_transactions.csv`
- Profil-Reports: `outputs/users/<profil>/`
- Legacy-Fallback (alt): `data/incoming/`, `data/final_transactions.csv`, `outputs/`

## Mehrbenutzer-/Mehrkonto-Workflow

- Sidebar-Schalter `Benutzer / Konto` zum Wechseln zwischen Profilen.
- `Neues Profil anlegen`: erstellt automatisch Daten- und Output-Ordner je Profil.
- `Profil loeschen` mit Sicherheits-Checkbox (Profil `Mario` ist als Basiskonto geschützt).
- Profilanzeige im Header ist hervorgehoben und mit lesbarem Namen formatiert.
- Import und Pipeline laufen immer nur im aktiven Profilkontext.

## CSV-Import im Dashboard

- Im Dashboard gibt es den Bereich `📥 CSV-Import`.
- Ablauf:
  1. CSV-Datei auswaehlen
  2. Datei wird in `data/users/<profil>/incoming/` gespeichert
  3. `Importieren und Auswertung aktualisieren` starten
  4. Pipeline wird ausgefuehrt und Dashboard neu geladen

Hinweis: Reinkopieren einer Datei allein verarbeitet noch nichts. Die Verarbeitung passiert beim Pipeline-Run (ueber den Import-Button oder `python src/run_pipeline.py`).

## Hinweise zur Kategorisierung

- Regeln sind in `src/category_rules.py` priorisiert (erste passende Regel gewinnt).
- Generische Zahlungsanbieter werden kontextbasiert ueber Verwendungszweck/Buchungstext interpretiert.
- Spezifische Empfaengerregeln (z. B. Werkstatt, Mobilfunk, Baumarkt, Versicherer) wurden gezielt erweitert.
- Neu hinzugefuegte Kategorien/Regeln aus der letzten Ueberarbeitung:
  - `dining.school_meals` (z. B. SFZ CoWerk)
  - `personal.haircare` (z. B. Salon Schnittpunkt)
  - verfeinerte Zuordnung fuer Kino (`kinoheld`, `Repp Mediumtechnik`)
  - verfeinerte Versorger-Zuordnung (`ROEBEN GAS` -> `housing.utilities`)

## Stand der letzten Ueberarbeitung

- Kategorie-Qualitaet deutlich verbessert; `uncategorized` stark reduziert.
- Dashboard verbessert (Farben, Hovertexte, Zeitraumanzeige, Kontostandverlauf, zusammengefasste Kategorien).
- Datumsfilter robust (Schnellwahl + gemeinsamer manueller Datumsbereich stabil synchronisiert).
- Anzeige-/Encoding-Artefakte in Textfeldern entschärft.
- Mehrprofilbetrieb aktiv: getrennte Datenablage und Auswertung pro Benutzer/Konto.
