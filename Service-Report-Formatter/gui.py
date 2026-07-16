#!/usr/bin/env python3
"""Grafische Oberfläche (Tkinter) für den Service-Report-Formatter.

Diese Datei ist nur die "Hülle": Sie sammelt Eingaben aus dem Fenster und ruft
dieselben, bereits getesteten Funktionen auf wie die Kommandozeilen-Version
(build_request, call_anthropic, parse_response, render_report).

Start:  python gui.py
"""
import io
import os
import queue
import threading
import tkinter as tk
from contextlib import redirect_stderr
from tkinter import filedialog, messagebox, scrolledtext, ttk

from extractor import build_request, call_anthropic, parse_response
from renderer import render_report

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11 – sollte hier nicht vorkommen
    tomllib = None


def _load_defaults():
    """Liest Vorbelegungen aus config.toml (falls vorhanden), sonst config.toml.example."""
    defaults = {
        "number": "",
        "customer_number": "",
        "customer_name": "",
        "default_year": "2026",
        "model": "claude-sonnet-4-6",
    }
    for path in ("config.toml", "config.toml.example"):
        if tomllib and os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    cfg = tomllib.load(f)
                inv = cfg.get("invoice", {})
                defaults["number"] = inv.get("number", defaults["number"])
                defaults["customer_number"] = inv.get("customer_number", defaults["customer_number"])
                defaults["customer_name"] = inv.get("customer_name", defaults["customer_name"])
                defaults["default_year"] = str(cfg.get("dates", {}).get("default_year", defaults["default_year"]))
                defaults["model"] = cfg.get("api", {}).get("model", defaults["model"])
            except Exception:
                pass  # bei kaputter Config einfach bei den Standardwerten bleiben
            break
    return defaults


class App:
    def __init__(self, root):
        self.root = root
        root.title("Service-Report-Formatter")
        root.geometry("900x760")

        d = _load_defaults()

        # --- Kopfbereich: Rechnungs-/Kundendaten ---
        top = ttk.LabelFrame(root, text="Rechnungsdaten (gehen NICHT an das Modell)")
        top.pack(fill="x", padx=10, pady=(10, 5))

        self.var_number = tk.StringVar(value=d["number"])
        self.var_customer_number = tk.StringVar(value=d["customer_number"])
        self.var_customer_name = tk.StringVar(value=d["customer_name"])
        self.var_year = tk.StringVar(value=d["default_year"])
        self.var_model = tk.StringVar(value=d["model"])

        self._labeled_entry(top, "Rechnungsnummer", self.var_number, 0, 0)
        self._labeled_entry(top, "Kundennummer", self.var_customer_number, 0, 2)
        self._labeled_entry(top, "Kundenname", self.var_customer_name, 1, 0)
        self._labeled_entry(top, "Jahr (für Daten ohne Jahr)", self.var_year, 1, 2)
        self._labeled_entry(top, "Modell", self.var_model, 2, 0)

        # --- API-Key ---
        keyframe = ttk.LabelFrame(root, text="API-Key")
        keyframe.pack(fill="x", padx=10, pady=5)
        env_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.var_key = tk.StringVar(value=env_key)
        ttk.Label(keyframe, text="ANTHROPIC_API_KEY").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.key_entry = ttk.Entry(keyframe, textvariable=self.var_key, show="*", width=60)
        self.key_entry.grid(row=0, column=1, sticky="we", padx=5, pady=5)
        self.show_key = tk.BooleanVar(value=False)
        ttk.Checkbutton(keyframe, text="anzeigen", variable=self.show_key,
                        command=self._toggle_key).grid(row=0, column=2, padx=5)
        keyframe.columnconfigure(1, weight=1)

        # --- Notizen ---
        notesframe = ttk.LabelFrame(root, text="Arbeitsnotizen")
        notesframe.pack(fill="both", expand=True, padx=10, pady=5)
        btnrow = ttk.Frame(notesframe)
        btnrow.pack(fill="x", padx=5, pady=5)
        ttk.Button(btnrow, text="Datei laden …", command=self._load_file).pack(side="left")
        ttk.Button(btnrow, text="Beispielnotizen laden", command=self._load_example).pack(side="left", padx=5)
        self.notes = scrolledtext.ScrolledText(notesframe, height=10, wrap="word")
        self.notes.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        # --- Aktionen ---
        actions = ttk.Frame(root)
        actions.pack(fill="x", padx=10, pady=5)
        self.btn_run = ttk.Button(actions, text="Report erstellen (API)", command=self._run)
        self.btn_run.pack(side="left")
        ttk.Button(actions, text="Vorschau ohne API (Dry-Run)", command=self._dry_run).pack(side="left", padx=5)
        ttk.Button(actions, text="Report speichern …", command=self._save).pack(side="left")

        # --- Status / Warnungen ---
        self.status = tk.StringVar(value="Bereit.")
        ttk.Label(root, textvariable=self.status, foreground="#555").pack(fill="x", padx=12, pady=(0, 2))

        # --- Ausgabe ---
        outframe = ttk.LabelFrame(root, text="Report")
        outframe.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.output = scrolledtext.ScrolledText(outframe, height=12, wrap="word")
        self.output.pack(fill="both", expand=True, padx=5, pady=5)

        self._result_queue = queue.Queue()

    # ---------- kleine Helfer ----------
    def _labeled_entry(self, parent, label, var, row, col):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=5, pady=4)
        entry = ttk.Entry(parent, textvariable=var, width=28)
        entry.grid(row=row, column=col + 1, sticky="we", padx=5, pady=4)
        parent.columnconfigure(col + 1, weight=1)

    def _toggle_key(self):
        self.key_entry.config(show="" if self.show_key.get() else "*")

    def _load_file(self):
        path = filedialog.askopenfilename(title="Notizdatei wählen",
                                          filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")])
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.notes.delete("1.0", "end")
                    self.notes.insert("1.0", f.read())
                self.status.set(f"Geladen: {path}")
            except OSError as e:
                messagebox.showerror("Fehler", f"Datei konnte nicht gelesen werden:\n{e}")

    def _load_example(self):
        path = "examples/notes.txt"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.notes.delete("1.0", "end")
                self.notes.insert("1.0", f.read())
            self.status.set("Beispielnotizen geladen.")
        else:
            messagebox.showwarning("Nicht gefunden", f"{path} existiert nicht.")

    def _build_cfg(self):
        """Baut das cfg-dict aus den Feldern und prüft Pflichtwerte.

        Gibt (cfg, None) zurück oder (None, fehlermeldung).
        """
        number = self.var_number.get().strip()
        customer_number = self.var_customer_number.get().strip()
        customer_name = self.var_customer_name.get().strip()
        year_raw = self.var_year.get().strip()
        model = self.var_model.get().strip()

        missing = []
        if not number:
            missing.append("Rechnungsnummer")
        if not customer_number:
            missing.append("Kundennummer")
        if not customer_name:
            missing.append("Kundenname")
        if not model:
            missing.append("Modell")
        if not year_raw:
            missing.append("Jahr")
        if missing:
            return None, "Bitte ausfüllen: " + ", ".join(missing)

        try:
            year = int(year_raw)
        except ValueError:
            return None, "Jahr muss eine Zahl sein (z. B. 2026)."

        cfg = {
            "invoice": {"number": number, "customer_number": customer_number, "customer_name": customer_name},
            "dates": {"default_year": year},
            "api": {"model": model},
        }
        return cfg, None

    def _read_system_prompt(self):
        with open("prompts/system.md", "r", encoding="utf-8") as f:
            return f.read()

    def _set_output(self, text):
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)

    # ---------- Aktionen ----------
    def _dry_run(self):
        cfg, err = self._build_cfg()
        if err:
            messagebox.showwarning("Eingabe unvollständig", err)
            return
        notes = self.notes.get("1.0", "end").strip()
        if not notes:
            messagebox.showwarning("Keine Notizen", "Bitte Notizen eingeben oder eine Datei laden.")
            return
        import json
        request = build_request(self._read_system_prompt(), notes, model=cfg["api"]["model"])
        self._set_output(json.dumps(request, indent=2, ensure_ascii=False))
        self.status.set("Dry-Run: Request gebaut, KEIN API-Aufruf.")

    def _run(self):
        cfg, err = self._build_cfg()
        if err:
            messagebox.showwarning("Eingabe unvollständig", err)
            return
        notes = self.notes.get("1.0", "end").strip()
        if not notes:
            messagebox.showwarning("Keine Notizen", "Bitte Notizen eingeben oder eine Datei laden.")
            return
        api_key = self.var_key.get().strip()
        if not api_key:
            messagebox.showwarning("Kein API-Key", "Bitte einen ANTHROPIC_API_KEY eingeben.")
            return

        request = build_request(self._read_system_prompt(), notes, model=cfg["api"]["model"])

        # API-Aufruf im Hintergrund-Thread, damit das Fenster nicht einfriert.
        self.btn_run.config(state="disabled")
        self.status.set("Sende an Claude … bitte warten.")

        def worker():
            try:
                raw = call_anthropic(request, api_key=api_key)
                parsed = parse_response(raw)
                # Monatswarnung geht in render_report auf stderr – wir fangen sie ab.
                buf = io.StringIO()
                with redirect_stderr(buf):
                    out_text = render_report(parsed, cfg)
                self._result_queue.put(("ok", out_text, buf.getvalue().strip()))
            except Exception as e:  # RuntimeError (API), ValueError (ungültiges Datum), …
                self._result_queue.put(("err", str(e), ""))

        threading.Thread(target=worker, daemon=True).start()
        self._poll_result()

    def _poll_result(self):
        """Prüft regelmäßig, ob der Hintergrund-Thread fertig ist (thread-sicher)."""
        try:
            kind, payload, extra = self._result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_result)
            return

        self.btn_run.config(state="normal")
        if kind == "ok":
            self._set_output(payload)
            if extra:
                self.status.set("Fertig — Warnung: " + extra)
            else:
                self.status.set("Fertig.")
        else:
            self.status.set("Fehler.")
            messagebox.showerror("Fehler", payload)

    def _save(self):
        text = self.output.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Nichts zu speichern", "Es gibt keinen Report zum Speichern.")
            return
        path = filedialog.asksaveasfilename(title="Report speichern", defaultextension=".txt",
                                            initialfile="report.txt",
                                            filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")])
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.status.set(f"Gespeichert: {path}")
            except OSError as e:
                messagebox.showerror("Fehler", f"Konnte nicht speichern:\n{e}")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
