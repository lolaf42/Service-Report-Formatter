# Service-Report-Formatter

Ein Werkzeug, das formlose Arbeitsnotizen aus Serviceeinsätzen in einen
rechnungsfähigen Service-Report umwandelt. Die Umwandlung läuft über die
Anthropic-API (Claude), weil der Input unstrukturiert ist und nicht mit festen
Regeln (Regex) erfasst werden kann. Nutzbar wahlweise über die Kommandozeile
(CLI) oder eine grafische Oberfläche (GUI).

## Was das Tool tut

1. Liest formlose Notizen (Stichpunkte, Fließtext, gemischte Datumsformate).
2. Schickt sie an Claude und erhält eine **strukturierte JSON-Zwischenrepräsentation** zurück.
3. Löst offene Jahresangaben auf, validiert Datumswerte, sortiert chronologisch
   und rendert einen sauberen Textblock – gegliedert nach Datum, jeder Tagesblock
   eigenständig kopierbar.

Rechnungs- und Kundennummer stehen ausschließlich in der Konfiguration und werden
**erst beim Rendern** eingesetzt – sie gehen nie an das Modell.

## Projektstruktur

| Datei | Aufgabe |
|-------|---------|
| `report.py` | CLI-Einstiegspunkt: argparse, Ein-/Ausgabe, Flag-Validierung |
| `gui.py` | Grafische Oberfläche (Tkinter) |
| `config.py` | Config laden, validieren, CLI-Overrides anwenden |
| `extractor.py` | API-Request bauen, Anthropic aufrufen, JSON robust parsen |
| `renderer.py` | JSON + Config → finaler Textblock (ohne Netzwerk testbar) |
| `prompts/system.md` | Systemprompt (ohne Codeänderung anpassbar) |
| `config.toml.example` | Beispielkonfiguration |
| `examples/` | Beispiel-Notizen und erwartete Ausgabe |
| `tests/` | Tests (Rendering, Jahresauflösung, Flag-Kombinationen, …) |
| `launch-gui.sh` | Startskript der GUI (mit Fehler-Log) |
| `install-app.sh` | Installiert das Tool als Desktop-Anwendung (Linux/GNOME) |
| `service-report-formatter.desktop` | Vorlage für den Desktop-Eintrag |
| `.vscode/launch.json` | VS-Code-Debug-Konfiguration (dry-run) |

## Installation

Voraussetzung: Python 3.11+ (das Tool nutzt `tomllib` aus der Standardbibliothek).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Den API-Key als Umgebungsvariable setzen (niemals in Config oder Code):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Vorlage siehe `.env.example`.

## Konfiguration

Alle variablen Werte stehen in `config.toml`. Kopiervorlage:

```bash
cp config.toml.example config.toml
```

```toml
[invoice]
number = "RE-2026-03-001"      # feste Rechnungsnummer für diesen Lauf
customer_number = "K-1042"     # feste Kundennummer
customer_name = "Beispiel GmbH"

[dates]
default_year = 2026            # Jahr für Datumsangaben ohne Jahresangabe

[api]
model = "claude-sonnet-4-6"
```

Fehlt ein Pflichtwert, bricht das Programm mit einer klaren Meldung ab und nennt den
fehlenden Schlüssel (kein stiller Default).

## Verwendung (CLI)

```bash
# Aus Datei, Ausgabe in Datei
python report.py --input examples/notes.txt --output report.txt

# Aus stdin
cat examples/notes.txt | python report.py --stdin

# Anderer Config-Pfad
python report.py --input notes.txt --config pfad.toml
```

### CLI-Overrides (Flag schlägt Config)

Jeder Config-Wert ist einzeln per Flag überschreibbar:

```bash
python report.py --input notes.txt \
  --invoice-number RE-2026-04-002 \
  --customer-number K-2000 \
  --customer-name "Muster AG" \
  --year 2025 \
  --model claude-sonnet-4-6
```

### Weitere Flags

| Flag | Wirkung |
|------|---------|
| `--dry-run` | Baut den Request zusammen und gibt ihn aus, ruft die API **nicht** auf |
| `--save-json pfad.json` | Schreibt die geparste Modellantwort zusätzlich als JSON weg |
| `--from-json pfad.json` | Überspringt den API-Call komplett und rendert aus der Datei |

Unzulässige Flag-Kombinationen führen zu einem klaren Abbruch:
`--from-json` zusammen mit `--input`, `--stdin`, `--save-json` oder `--dry-run`;
sowie das Fehlen von `--input`, `--stdin` **und** `--from-json`.

## Grafische Oberfläche (GUI)

Alternativ zur Kommandozeile gibt es eine einfache Fenster-Oberfläche (Tkinter):

```bash
python gui.py
```

Darin: Rechnungs-/Kundendaten und API-Key eingeben, Notizen tippen oder per
„Datei laden" öffnen, dann „Report erstellen (API)". „Vorschau ohne API (Dry-Run)"
zeigt den Request ohne API-Aufruf. Der API-Aufruf läuft im Hintergrund, damit das
Fenster nicht einfriert.

Tkinter ist in Python enthalten; auf manchen Linux-Systemen muss einmalig das
Systempaket installiert werden:

```bash
sudo apt install python3-tk
```

## Als Desktop-Anwendung installieren (Linux/GNOME)

Damit das Tool wie eine normale App im Anwendungsmenü erscheint und per Klick
gestartet werden kann:

```bash
./install-app.sh
```

Das Skript erzeugt den Menü-Eintrag mit den Pfaden des aktuellen Nutzers und
aktualisiert die Menü-Datenbank. Anschließend die App über die Super-Taste und
Eingabe von „Service" starten.

> Hinweis (Ubuntu/GNOME): Neu installierte Einträge erscheinen manchmal erst nach
> einem Ab- und Anmelden. Das direkte Doppelklicken der `.desktop`-Datei im
> Dateimanager ist in aktuellen GNOME-Versionen deaktiviert – daher über das
> Anwendungsmenü starten.

## Datums- und Monatsbehandlung

Das Modell gibt Datumswerte als explizites Objekt zurück, nie als String:

| Fall | Rückgabe | Behandlung in Python |
|------|----------|----------------------|
| Datum vollständig | `{"year": 2026, "month": 3, "day": 12}` | direkt verwendet |
| Nur Tag+Monat | `{"year": null, "month": 3, "day": 12}` | mit `default_year` vervollständigt |
| Kein Datum | `null` | landet unter „Nicht zugeordnet" |

`date: null` und `year: null` sind getrennte Fälle und werden nicht vermischt.
Ungültige Datumswerte (z. B. `month: 13`, `31.02.`) werden in Python validiert und abgefangen.

**Monatsprüfung:** Ein Lauf bildet einen Monat / eine Rechnungsnummer ab. Enthält der
Input nach der Jahresauflösung Daten aus mehr als einem Monat, gibt das Programm eine
deutliche Warnung auf stderr aus und nennt die betroffenen Monate. Es bricht nicht ab.

## Tests

```bash
python -m pytest
```

Abgedeckt sind u. a.: Rendering inkl. Kopfzeile, Jahresauflösung bei `year: null`,
Verhalten bei `date: null` und die Abgrenzung beider Fälle, chronologische Sortierung,
Monatswarnung bei gemischten Monaten, „Flag schlägt Config", Abbruch bei fehlendem
Pflichtwert, Abbruch bei jeder unzulässigen Flag-Kombination, ungültiges Datum aus der
Modellantwort und JSON-Parsing mit Markdown-Fences.

## VS Code

`.vscode/launch.json` enthält eine Debug-Konfiguration, die
`report.py --input examples/notes.txt --dry-run` ausführt.
