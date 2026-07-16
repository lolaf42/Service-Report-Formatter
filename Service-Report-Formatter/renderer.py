from datetime import date
import datetime
import sys


def _validate_date(d: dict):
    # d has keys year, month, day where year may be None
    if d is None:
        return None
    y = d.get("year")
    m = d.get("month")
    day = d.get("day")
    if y is None:
        return None
    try:
        return datetime.date(int(y), int(m), int(day))
    except Exception as e:
        raise ValueError(f"Invalid date from model: {d}: {e}")


def render_report(parsed: dict, cfg: dict) -> str:
    entries = parsed.get("entries", [])
    open_q = parsed.get("open_questions") or []

    default_year = cfg["dates"]["default_year"]

    dated = []
    undated = []

    for e in entries:
        d = e.get("date")
        if d is None:
            undated.append(e)
            continue
        # if year is null, resolve to default_year
        if d.get("year") is None:
            d = {**d, "year": default_year}
        # validate
        try:
            _ = _validate_date(d)
        except ValueError as ve:
            raise
        e["_date_obj"] = datetime.date(int(d["year"]), int(d["month"]), int(d["day"]))
        dated.append(e)

    # check months
    months = set((e["_date_obj"].year, e["_date_obj"].month) for e in dated)
    if len(months) > 1:
        months_list = sorted(months)
        mm = ", ".join(f"{m:02d}.{y}" for (y, m) in months_list)
        print(f"WARNING: Entries span multiple months: {mm}", file=sys.stderr)

    # sort chronologically
    dated.sort(key=lambda x: x["_date_obj"]) 

    lines = []
    inv = cfg["invoice"]
    lines.append(f"Rechnungsnummer: {inv['number']}")
    lines.append(f"Kundennummer: {inv['customer_number']}")
    lines.append(f"Kunde: {inv['customer_name']}")
    lines.append("")

    for e in dated:
        d = e["_date_obj"]
        hours = e.get("hours")
        date_line = d.strftime("%d.%m.%Y")
        if hours is not None:
            date_line = f"{date_line} — {hours} h"
        lines.append(date_line)
        text = e.get("text", "").strip()
        # ensure single paragraph, no bullets
        text = " ".join(line.strip() for line in text.splitlines() if line.strip())
        if not text:
            text = "(keine Leistungsbeschreibung)"
        lines.append(text)
        lines.append("")

    if undated:
        lines.append("Nicht zugeordnet:")
        lines.append("")
        for e in undated:
            text = e.get("text", "").strip()
            text = " ".join(line.strip() for line in text.splitlines() if line.strip())
            lines.append(text)
            lines.append("")

    if open_q:
        lines.append("Offene Punkte:")
        for q in open_q:
            lines.append(f"- {q}")

    return "\n".join(lines)
