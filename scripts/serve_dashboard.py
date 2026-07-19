"""Serve the spend dashboard as a small local web app with a live Refresh.

The page's Refresh button POSTs /api/refresh, which pulls fresh data from
Plaid, recomputes the model, and returns it — the page re-renders in place.

  python scripts/serve_dashboard.py                 # live, localhost only
  python scripts/serve_dashboard.py --host 0.0.0.0  # reachable on your LAN
  python scripts/serve_dashboard.py --from-csv data/transactions.csv  # no Plaid

Localhost is reachable only from this Mac. Use --host 0.0.0.0 to open it to
your home Wi-Fi (then visit http://<this-mac-ip>:8000 from your phone). To
reach it from anywhere you'd add a tunnel + authentication — ask if you want
that; exposing financial data publicly needs a login in front of it.
"""
import argparse
import errno
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import _bootstrap  # noqa: F401

from generate_dashboard import compute_model, load_from_csv, load_live, WINDOW_DAYS
from src.template_dashboard import render_html


class State:
    """Holds the current model; rebuilds it (a live pull) on demand."""

    def __init__(self, source):
        self.source = source
        self.lock = threading.Lock()
        self.model = None

    def rebuild(self):
        with self.lock:
            self.model = compute_model(self.source())
            return self.model

    def get(self):
        return self.model if self.model is not None else self.rebuild()


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, render_html(state.get()).encode("utf-8"),
                           "text/html; charset=utf-8")
            elif self.path == "/api/model":
                self._send(200, json.dumps(state.get()).encode("utf-8"),
                           "application/json")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            if self.path == "/api/refresh":
                try:
                    model = state.rebuild()
                except Exception as e:
                    self._send(500, json.dumps({"error": str(e)}).encode("utf-8"),
                               "application/json")
                    return
                self._send(200, json.dumps(model).encode("utf-8"), "application/json")
            else:
                self._send(404, b"not found", "text/plain")

        def log_message(self, *args):
            pass  # quiet

    return Handler


def main(argv=None):
    p = argparse.ArgumentParser(description="Serve the spend dashboard")
    p.add_argument("--from-csv", dest="csv", help="Serve from a CSV (no Plaid)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--days", type=int, default=WINDOW_DAYS + 20)
    a = p.parse_args(argv)

    source = (lambda: load_from_csv(a.csv)) if a.csv else (lambda: load_live(a.days))
    state = State(source)
    state.rebuild()  # fail fast if config/credentials are wrong

    if a.host == "0.0.0.0":
        print("WARNING: --host 0.0.0.0 exposes the dashboard to everyone on your "
              "network. Only do this on a trusted home Wi-Fi.")

    try:
        server = ThreadingHTTPServer((a.host, a.port), make_handler(state))
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            print(f"Port {a.port} is already in use — another server is probably "
                  f"still running.\n"
                  f"  Stop it:  lsof -ti tcp:{a.port} | xargs kill\n"
                  f"  Or pick another port:  --port {a.port + 1}")
            return
        raise
    print(f"Serving dashboard on http://{a.host}:{a.port}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
