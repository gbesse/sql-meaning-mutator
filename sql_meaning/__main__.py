import json
from pathlib import Path
import sqlite3
import sys

from .engine import compare, search

ROOT = Path(__file__).resolve().parent
MESSAGES = {
    "fr": {"help":"Utilisation : python -m sql_meaning demo|search dossier.json|compare dossier.json|serve [port] [--lang fr|en|es]", "error":"Entrée non valide", "ready":"Laboratoire SQL local"},
    "en": {"help":"Usage: python -m sql_meaning demo|search case.json|compare case.json|serve [port] [--lang fr|en|es]", "error":"Invalid input", "ready":"Local SQL laboratory"},
    "es": {"help":"Uso: python -m sql_meaning demo|search caso.json|compare caso.json|serve [puerto] [--lang fr|en|es]", "error":"Entrada no válida", "ready":"Laboratorio SQL local"},
}


def example():
    return json.loads((ROOT / "examples/revenue.json").read_text())


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    lang = "en"
    if "--lang" in args:
        i = args.index("--lang")
        if i+1 < len(args) and args[i+1] in MESSAGES:
            lang = args[i+1]
        del args[i:i+2]
    message = MESSAGES[lang]
    try:
        if not args or args[0] in ("help", "--help"):
            print(message["help"])
            return 0
        command = args.pop(0)
        if command == "demo":
            result = search(example())
        elif command == "search" and len(args) == 1:
            result = search(json.loads(Path(args[0]).read_text()))
        elif command == "compare" and len(args) == 1:
            result = compare(json.loads(Path(args[0]).read_text()))
        elif command == "serve":
            from .server import serve
            port = int(args[0]) if args else 8766
            print(f'{message["ready"]}: http://127.0.0.1:{port}/?lang={lang}', flush=True)
            serve(port)
            return 0
        else:
            print(message["help"], file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 1 if result.get("status") == "counterexample" or result.get("equal") is False else 2 if result.get("status") == "query_or_fixture_error" else 0
    except (ValueError, TypeError, KeyError, OSError, sqlite3.Error):
        print(json.dumps({"error":"invalid_input", "message":message["error"]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
