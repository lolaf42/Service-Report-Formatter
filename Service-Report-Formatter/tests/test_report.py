"""Testet die Flag-Validierung in report.main().

Unzulässige Flag-Kombinationen müssen zu einem klaren Abbruch (SystemExit) führen,
bevor irgendein API-Aufruf oder Datei-Lesen passiert.
"""
import pytest
from report import main


def test_from_json_with_input_aborts():
    with pytest.raises(SystemExit):
        main(["--from-json", "x.json", "--input", "notes.txt"])


def test_from_json_with_stdin_aborts():
    with pytest.raises(SystemExit):
        main(["--from-json", "x.json", "--stdin"])


def test_from_json_with_save_json_aborts():
    with pytest.raises(SystemExit):
        main(["--from-json", "x.json", "--save-json", "out.json"])


def test_from_json_with_dry_run_aborts():
    with pytest.raises(SystemExit):
        main(["--from-json", "x.json", "--dry-run"])


def test_no_source_aborts():
    with pytest.raises(SystemExit):
        main([])


def test_input_and_stdin_are_mutually_exclusive():
    # --input und --stdin liegen in einer argparse-Gruppe -> Abbruch.
    with pytest.raises(SystemExit):
        main(["--input", "notes.txt", "--stdin"])


def test_missing_from_json_file_aborts_cleanly():
    # Nicht existierende JSON-Datei -> sauberer Abbruch, kein Traceback.
    with pytest.raises(SystemExit):
        main(["--from-json", "gibtsnicht.json", "--config", "config.toml.example"])


def test_missing_input_file_aborts_cleanly():
    with pytest.raises(SystemExit):
        main(["--input", "gibtsnicht.txt", "--config", "config.toml.example", "--dry-run"])
