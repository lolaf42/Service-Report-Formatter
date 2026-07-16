import tomllib
import sys
from types import SimpleNamespace
import os

from config import load_config


def test_overrides(tmp_path):
    cfg_file = tmp_path / "cfg.toml"
    cfg_file.write_text("""
[invoice]
number = "A"
customer_number = "C"
customer_name = "N"

[dates]
default_year = 2025

[api]
model = "m"
""")
    args = SimpleNamespace(config=str(cfg_file), invoice_number="B", customer_number=None, customer_name=None, year=2026, model="m2")
    cfg = load_config(args)
    assert cfg["invoice"]["number"] == "B"
    assert cfg["dates"]["default_year"] == 2026
    assert cfg["api"]["model"] == "m2"


def test_missing_keys(tmp_path, monkeypatch):
    cfg_file = tmp_path / "bad.toml"
    cfg_file.write_text("""
[invoice]
customer_number = "C"
""")
    args = SimpleNamespace(config=str(cfg_file), invoice_number=None, customer_number=None, customer_name=None, year=None, model=None)
    try:
        load_config(args)
        assert False, "should have exited"
    except SystemExit as e:
        assert "invoice.number" in str(e) or "invoice.customer_name" in str(e)
