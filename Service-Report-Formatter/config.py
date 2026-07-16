"""Lädt die Konfiguration aus einer TOML-Datei, wendet CLI-Overrides an und
validiert, dass alle Pflichtwerte vorhanden sind.

tomllib ist seit Python 3.11 Teil der Standardbibliothek – keine Zusatzabhängigkeit.
"""
import tomllib
import sys


def load_config(args):
    """Gibt ein verschachteltes dict mit der finalen Konfiguration zurück.

    Reihenfolge: Datei laden -> CLI-Flags überschreiben Werte -> Pflichtwerte prüfen.
    Ein CLI-Flag schlägt also immer den Wert aus der Config.
    """
    path = args.config
    try:
        with open(path, "rb") as f:  # tomllib erwartet den Binärmodus ("rb")
            cfg = tomllib.load(f)
    except FileNotFoundError:
        sys.exit(f"Konfigurationsdatei nicht gefunden: {path}")

    # --- CLI-Overrides anwenden (Flag schlägt Config) ---
    inv = cfg.get("invoice", {})
    if getattr(args, "invoice_number", None):
        inv["number"] = args.invoice_number
    if getattr(args, "customer_number", None):
        inv["customer_number"] = args.customer_number
    if getattr(args, "customer_name", None):
        inv["customer_name"] = args.customer_name
    cfg["invoice"] = inv

    dates = cfg.get("dates", {})
    if getattr(args, "year", None):
        dates["default_year"] = args.year
    cfg["dates"] = dates

    api = cfg.get("api", {})
    if getattr(args, "model", None):
        api["model"] = args.model
    cfg["api"] = api

    # --- Pflichtwerte prüfen ---
    # Fehlt einer, brechen wir mit klarer Meldung ab statt einen Default zu raten.
    missing = []
    if not cfg.get("invoice") or not cfg["invoice"].get("number"):
        missing.append("invoice.number")
    if not cfg.get("invoice") or not cfg["invoice"].get("customer_number"):
        missing.append("invoice.customer_number")
    if not cfg.get("invoice") or not cfg["invoice"].get("customer_name"):
        missing.append("invoice.customer_name")
    if not cfg.get("dates") or cfg["dates"].get("default_year") is None:
        missing.append("dates.default_year")
    if not cfg.get("api") or not cfg["api"].get("model"):
        missing.append("api.model")

    if missing:
        sys.exit("Fehlende Pflichtwerte in der Konfiguration: " + ", ".join(missing))

    return cfg
