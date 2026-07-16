#!/usr/bin/env python3
import argparse
import sys
import os
import json

from config import load_config
from extractor import build_request, call_anthropic, parse_response
from renderer import render_report


def main(argv=None):
    p = argparse.ArgumentParser(prog="report.py")
    group = p.add_mutually_exclusive_group()
    p.add_argument("--config", default="config.toml")
    group.add_argument("--input")
    group.add_argument("--stdin", action="store_true")
    p.add_argument("--from-json")
    p.add_argument("--output")
    p.add_argument("--save-json")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--invoice-number")
    p.add_argument("--customer-number")
    p.add_argument("--customer-name")
    p.add_argument("--year", type=int)
    p.add_argument("--model")
    args = p.parse_args(argv)

    # invalid combinations
    if args.from_json and (args.input or args.stdin):
        p.error("--from-json cannot be used together with --input or --stdin")
    if args.from_json and args.save_json:
        p.error("--from-json cannot be used together with --save-json")
    if args.from_json and args.dry_run:
        p.error("--from-json cannot be used together with --dry-run")
    if not (args.input or args.stdin or args.from_json):
        p.error("One of --input, --stdin or --from-json must be provided")

    cfg = load_config(args)

    # Read source text
    if args.from_json:
        try:
            with open(args.from_json, "r", encoding="utf-8") as f:
                parsed = json.load(f)
        except FileNotFoundError:
            sys.exit(f"JSON-Datei nicht gefunden: {args.from_json}")
        except json.JSONDecodeError as e:
            sys.exit(f"JSON-Datei ist ungültig ({args.from_json}): {e}")
    else:
        if args.stdin:
            text = sys.stdin.read()
        else:
            try:
                with open(args.input, "r", encoding="utf-8") as f:
                    text = f.read()
            except FileNotFoundError:
                sys.exit(f"Eingabedatei nicht gefunden: {args.input}")

        with open("prompts/system.md", "r", encoding="utf-8") as f:
            system_prompt = f.read()
        # cfg["api"]["model"] enthält bereits einen etwaigen --model-Override (siehe config.py).
        request = build_request(system_prompt, text, model=cfg["api"]["model"])
        if args.dry_run:
            print(json.dumps(request, indent=2, ensure_ascii=False))
            return

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        try:
            raw = call_anthropic(request, api_key=api_key)
        except RuntimeError as e:
            sys.exit(str(e))
        parsed = parse_response(raw)

        if args.save_json:
            with open(args.save_json, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)

    out_text = render_report(parsed, cfg)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out_text)
    else:
        print(out_text)


if __name__ == "__main__":
    main()
