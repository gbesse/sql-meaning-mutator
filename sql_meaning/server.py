import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .__main__ import ROOT, example
from .engine import compare, search


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, code, data, kind="application/json"):
        content = data if isinstance(data, bytes) else json.dumps(data, allow_nan=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/example":
            case = example()
            return self.reply(200, {"case": case, "comparison": compare(case)})
        if path in ("/", "/app.js", "/style.css"):
            file = "index.html" if path == "/" else path[1:]
            kind = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css"}[file]
            return self.reply(200, (ROOT / "web" / file).read_bytes(), kind)
        self.reply(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/api/search":
            return self.reply(404, {"error": "not_found"})
        origin = self.headers.get("Origin")
        if origin and origin != f"http://127.0.0.1:{self.server.server_port}":
            return self.reply(403, {"error": "origin_denied"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 500_000:
                raise ValueError("invalid_size")
            case = json.loads(self.rfile.read(size))
            result = search(case, max_depth=2, max_cases=256, seconds=3)
            self.reply(200, result)
        except (ValueError, KeyError, TypeError):
            self.reply(400, {"error": "invalid_input", "messages": ["Entrée non valide", "Invalid input", "Entrada no válida"]})


def serve(port=8766):
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
