"""Baut den API-Request zusammen, ruft die Anthropic-API auf und parst die Antwort.

Der Netzwerk-Teil (call_anthropic) ist bewusst von build_request und
parse_response getrennt, damit die anderen Funktionen ohne Netzwerk testbar sind.
"""
import json
import re
import time


def build_request(system_prompt: str, user_text: str, model: str, max_tokens: int = 8000) -> dict:
    """Setzt die Bestandteile zu einem Messages-API-Request zusammen.

    Rechnungs- und Kundennummer gehen bewusst NICHT an das Modell – sie werden
    erst beim Rendern eingesetzt.
    """
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_text}],
    }


def call_anthropic(request: dict, api_key: str | None, max_retries: int = 3) -> str:
    """Ruft die Anthropic Messages-API auf und gibt den reinen Text zurück.

    Bei Timeouts, Rate-Limits, Verbindungs- oder Serverfehlern wird mit einfachem
    exponentiellem Backoff erneut versucht.
    """
    if not api_key:
        raise RuntimeError(
            "Umgebungsvariable ANTHROPIC_API_KEY ist nicht gesetzt. "
            "Bitte setzen (z. B. export ANTHROPIC_API_KEY=...)."
        )

    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "Das Paket 'anthropic' ist nicht installiert. Bitte 'pip install -r requirements.txt' ausführen."
        ) from e

    client = anthropic.Anthropic(api_key=api_key)

    retryable = (
        anthropic.APITimeoutError,
        anthropic.RateLimitError,
        anthropic.APIConnectionError,
        anthropic.InternalServerError,
    )

    last_exc = None
    for attempt in range(max_retries):
        try:
            resp = client.messages.create(**request)
            # resp.content ist eine Liste von Blöcken; wir sammeln alle Text-Blöcke ein.
            return "".join(block.text for block in resp.content if block.type == "text")
        except anthropic.AuthenticationError as e:
            # Nicht wiederholbar: Der Key ist ungültig. Klare Meldung statt Traceback.
            raise RuntimeError(
                "API-Key ungültig (401). Bitte einen gültigen ANTHROPIC_API_KEY setzen "
                "(zu bekommen unter console.anthropic.com → API Keys)."
            ) from e
        except retryable as e:
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s, ...
        except anthropic.APIStatusError as e:
            # Andere API-Fehler (z. B. 400, 403) sind nicht wiederholbar.
            raise RuntimeError(f"API-Fehler: {e}") from e

    raise RuntimeError(f"API-Aufruf nach {max_retries} Versuchen fehlgeschlagen: {last_exc}") from last_exc


def _strip_fences(s: str) -> str:
    """Entfernt umschließende Markdown-Code-Fences (```json ... ``` oder ``` ... ```)."""
    s = s.strip()
    # Führende Fence-Zeile (```json oder ```) inklusive Zeilenumbruch entfernen.
    s = re.sub(r"^```[^\n]*\n", "", s)
    # Abschließende Fence entfernen.
    s = re.sub(r"\n```\s*$", "", s)
    return s.strip()


def parse_response(raw: str) -> dict:
    """Parst die Modellantwort robust zu einem dict.

    Entfernt Markdown-Fences, sucht das erste JSON-Objekt und gibt bei einem
    Parsefehler {"_raw": <rohantwort>} zurück, statt zu crashen.
    """
    cleaned = _strip_fences(raw)

    start = cleaned.find("{")
    if start == -1:
        return {"_raw": raw}

    # Erster Versuch: ab der ersten geschweiften Klammer bis zum Ende.
    try:
        return json.loads(cleaned[start:])
    except json.JSONDecodeError:
        pass

    # Fallback: balancierte Klammern zählen, um das erste vollständige Objekt zu finden.
    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(cleaned[start:i + 1])
                except json.JSONDecodeError:
                    break

    return {"_raw": raw}
