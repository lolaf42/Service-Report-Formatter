#!/usr/bin/env bash
# Startet die GUI und schreibt eventuelle Fehler in eine Log-Datei,
# damit man beim Start aus dem Menue sieht, was schiefgeht.
cd "$(dirname "$0")" || exit 1
LOG="$HOME/.service-report-formatter.log"
{
  echo "===== Start: $(date) ====="
  exec ./.venv/bin/python ./gui.py
} >>"$LOG" 2>&1
