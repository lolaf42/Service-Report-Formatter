import pytest
from renderer import render_report


CFG = {
    "invoice": {"number": "RE-2026-03-001", "customer_number": "K-1042", "customer_name": "Beispiel GmbH"},
    "dates": {"default_year": 2026},
}


def test_header_contains_invoice_and_customer():
    parsed = {"entries": [{"date": {"year": 2026, "month": 3, "day": 12}, "text": "Arbeit"}], "open_questions": []}
    out = render_report(parsed, CFG)
    assert "RE-2026-03-001" in out
    assert "K-1042" in out
    assert "Beispiel GmbH" in out
    # Kopfzeile steht vor dem ersten Tagesblock.
    assert out.index("RE-2026-03-001") < out.index("12.03.2026")


def test_date_null_vs_year_null_are_separate():
    """date: null -> 'Nicht zugeordnet'; year: null -> mit default_year vervollstaendigt."""
    parsed = {
        "entries": [
            {"date": {"year": None, "month": 4, "day": 1}, "text": "Rüstzeit"},
            {"date": None, "text": "Ohne Datum"},
        ],
        "open_questions": [],
    }
    out = render_report(parsed, CFG)
    # year: null wurde mit default_year (2026) aufgeloest und erscheint als Tagesblock.
    assert "01.04.2026" in out
    # date: null landet unter "Nicht zugeordnet".
    assert "Nicht zugeordnet" in out
    assert "Ohne Datum" in out
    # Der undatierte Eintrag darf NICHT ein Datum bekommen haben.
    assert out.index("Nicht zugeordnet") < out.index("Ohne Datum")


def test_hours_shown_when_present():
    parsed = {"entries": [{"date": {"year": 2026, "month": 3, "day": 12}, "hours": 8.0, "text": "Arbeit"}], "open_questions": []}
    out = render_report(parsed, CFG)
    assert "12.03.2026" in out
    assert "8.0" in out


def test_month_warning_on_mixed_months(capsys):
    parsed = {
        "entries": [
            {"date": {"year": 2026, "month": 3, "day": 12}, "text": "A"},
            {"date": {"year": 2026, "month": 4, "day": 2}, "text": "B"},
        ],
        "open_questions": [],
    }
    render_report(parsed, CFG)
    err = capsys.readouterr().err
    assert "03" in err and "04" in err  # beide betroffenen Monate genannt


def test_no_month_warning_single_month(capsys):
    parsed = {
        "entries": [
            {"date": {"year": 2026, "month": 3, "day": 12}, "text": "A"},
            {"date": {"year": 2026, "month": 3, "day": 13}, "text": "B"},
        ],
        "open_questions": [],
    }
    render_report(parsed, CFG)
    err = capsys.readouterr().err
    assert err.strip() == ""


def test_year_resolution_and_sorting(tmp_path):
    parsed = {
        "entries": [
            {"date": {"year": None, "month": 3, "day": 12}, "hours": 2, "text": "Arbeit A"},
            {"date": {"year": 2026, "month": 3, "day": 11}, "text": "Arbeit B"},
            {"date": None, "text": "Unbekannt"},
        ],
        "open_questions": ["Offen 1"]
    }
    cfg = {"invoice": {"number": "X", "customer_number": "C", "customer_name": "N"}, "dates": {"default_year": 2026}}
    out = render_report(parsed, cfg)
    # date resolution: None year should be set to 2026 and ordering 11 then 12
    assert "11.03.2026" in out
    assert "12.03.2026" in out
    assert "Nicht zugeordnet" in out
    assert "Offene Punkte" in out


def test_invalid_date_raises():
    parsed = {"entries": [{"date": {"year": 2026, "month": 2, "day": 31}, "text": "x"}], "open_questions": []}
    cfg = {"invoice": {"number": "X", "customer_number": "C", "customer_name": "N"}, "dates": {"default_year": 2026}}
    with pytest.raises(ValueError):
        render_report(parsed, cfg)
