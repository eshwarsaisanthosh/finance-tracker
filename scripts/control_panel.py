"""A phone-friendly control panel for finance-tracker.

Runs a small local web server whose buttons trigger the same scripts you'd
otherwise run in the terminal (reports, dashboard rebuild). It shells out to
the existing scripts, so it stays decoupled from Plaid internals.

Access is gated by a passcode. Set CONTROL_PANEL_PASSCODE in your .env; if it's
missing, a random one is generated and printed at startup.

  .venv/bin/python scripts/control_panel.py            # localhost:8000
  .venv/bin/python scripts/control_panel.py --port 8100

To reach it from your phone, expose this local port over Tailscale — see
docs/phone-access.md. Do NOT bind it to a public interface without the passcode.
"""
import argparse
import errno
import hmac
import json
import os
import secrets
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import _bootstrap  # noqa: F401
from _bootstrap import PROJECT_ROOT

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

# Passcode: from .env, else a random one printed at startup.
PASSCODE = os.getenv("CONTROL_PANEL_PASSCODE") or ""

# Only these date windows are accepted (defends the subprocess call).
ALLOWED_WINDOWS = {
    "today", "last_2_days", "last_7_days", "mtd", "last_30_days",
}
RUN_TIMEOUT = 180  # seconds


def _python_bin():
    """Prefer the project venv's python; fall back to whatever launched us."""
    venv = PROJECT_ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.exists() else "python3"


def build_argv(action, window="last_7_days", notify=False, pull_all=False):
    """Map a UI action to an argv list. Raises ValueError on bad input."""
    if action == "report":
        if window not in ALLOWED_WINDOWS:
            raise ValueError(f"bad window: {window}")
        argv = [_python_bin(), "-m", "src.main", "--window", window]
        if pull_all:
            argv.append("--pull-all")
        if not notify:
            argv.append("--no-notify")
        return argv
    if action == "dashboard":
        return [_python_bin(), "scripts/generate_dashboard.py"]
    raise ValueError(f"unknown action: {action}")


def run_action(action, window="last_7_days", notify=False, pull_all=False):
    """Execute an action and return {ok, code, output}."""
    argv = build_argv(action, window, notify, pull_all)
    try:
        proc = subprocess.run(
            argv, cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            timeout=RUN_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": -1, "output": "Timed out."}
    out = (proc.stdout or "") + (proc.stderr or "")
    return {"ok": proc.returncode == 0, "code": proc.returncode, "output": out.strip()}


def _authorized(supplied):
    if not PASSCODE:
        return False
    return hmac.compare_digest(str(supplied or ""), PASSCODE)


def make_handler():
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                self._send(200, PAGE_HTML, "text/html; charset=utf-8")
                return
            if path == "/dashboard":
                q = parse_qs(urlparse(self.path).query)
                if not _authorized(q.get("p", [""])[0]):
                    self._send(401, "Unauthorized", "text/plain")
                    return
                f = PROJECT_ROOT / "dashboard.html"
                if not f.exists():
                    self._send(404, "No dashboard yet — rebuild it first.", "text/plain")
                    return
                self._send(200, f.read_bytes(), "text/html; charset=utf-8")
                return
            self._send(404, "not found", "text/plain")

        def do_POST(self):
            path = urlparse(self.path).path
            if not _authorized(self.headers.get("X-Passcode")):
                self._send(401, json.dumps({"error": "unauthorized"}))
                return
            if path == "/api/run":
                length = int(self.headers.get("Content-Length", 0) or 0)
                try:
                    body = json.loads(self.rfile.read(length) or b"{}")
                except json.JSONDecodeError:
                    self._send(400, json.dumps({"error": "bad json"}))
                    return
                try:
                    result = run_action(
                        body.get("action"),
                        window=body.get("window", "last_7_days"),
                        notify=bool(body.get("notify", False)),
                        pull_all=bool(body.get("pull_all", False)),
                    )
                except ValueError as e:
                    self._send(400, json.dumps({"error": str(e)}))
                    return
                self._send(200, json.dumps(result))
                return
            self._send(404, json.dumps({"error": "not found"}))

        def log_message(self, *args):
            pass  # quiet

    return Handler


PAGE_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>finance-tracker</title>
<style>
:root { color-scheme: light dark; --bg:#f6f6f4; --card:#fff; --line:#e2e1da; --tx:#1c1c1a; --mut:#6b6a64; --acc:#185fa5; }
@media (prefers-color-scheme: dark){ :root{ --bg:#161614; --card:#232320; --line:#38372f; --tx:#f0efe8; --mut:#a2a199; --acc:#85b7eb; } }
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
body { margin:0; font:16px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:var(--bg); color:var(--tx); padding:16px; padding-bottom:40px; }
h1 { font-size:20px; font-weight:600; margin:4px 0 2px; }
.sub { color:var(--mut); font-size:13px; margin:0 0 18px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; margin-bottom:14px; }
.lbl { font-size:13px; color:var(--mut); font-weight:600; margin:0 0 10px; }
button { font:inherit; width:100%; padding:14px; border:1px solid var(--line); background:var(--card); color:var(--tx); border-radius:12px; cursor:pointer; }
button:active { transform:scale(0.98); }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.chip { padding:10px; font-size:14px; text-align:center; }
.chip.on { background:var(--acc); color:#fff; border-color:var(--acc); }
.run { background:var(--acc); color:#fff; border-color:var(--acc); font-weight:600; padding:16px; font-size:17px; }
.row { display:flex; align-items:center; gap:10px; }
input[type=checkbox]{ width:22px; height:22px; }
input[type=password]{ width:100%; padding:14px; font:inherit; border:1px solid var(--line); border-radius:12px; background:var(--card); color:var(--tx); }
pre { background:var(--bg); border:1px solid var(--line); border-radius:12px; padding:12px; font-size:12px; white-space:pre-wrap; word-break:break-word; max-height:320px; overflow:auto; margin:0; }
.hide { display:none; }
a.view { display:block; text-align:center; text-decoration:none; color:var(--acc); padding:14px; }
.err { color:#c0392b; font-size:13px; }
</style></head><body>

<div id="login" class="card">
  <h1>finance-tracker</h1>
  <p class="sub">Enter your passcode to continue.</p>
  <input type="password" id="pass" placeholder="Passcode" autocomplete="off">
  <p id="loginerr" class="err"></p>
  <button class="run" style="margin-top:10px" onclick="unlock()">Unlock</button>
</div>

<div id="app" class="hide">
  <h1>finance-tracker</h1>
  <p class="sub">Your Mac does the work; this is the remote.</p>

  <div class="card">
    <p class="lbl">Date range</p>
    <div class="grid" id="ranges">
      <button class="chip" data-r="today">Today</button>
      <button class="chip on" data-r="last_7_days">Last 7 days</button>
      <button class="chip" data-r="mtd">Month to date</button>
      <button class="chip" data-r="last_30_days">Last 30 days</button>
    </div>
    <div class="row" style="margin-top:14px"><input type="checkbox" id="pullall"><label for="pullall">Include all accounts</label></div>
    <div class="row" style="margin-top:10px"><input type="checkbox" id="notify"><label for="notify">Send push notification</label></div>
    <button class="run" style="margin-top:14px" onclick="run('report')">Run report</button>
  </div>

  <div class="card">
    <p class="lbl">Dashboard</p>
    <button onclick="run('dashboard')">Rebuild dashboard</button>
    <a class="view" id="viewlink" href="#" target="_blank">Open dashboard &rarr;</a>
  </div>

  <div class="card">
    <p class="lbl">Output</p>
    <pre id="out">Ready.</pre>
  </div>
</div>

<script>
var pass = "", range = "last_7_days";
function unlock(){
  pass = document.getElementById('pass').value;
  fetch('/api/run', {method:'POST', headers:{'X-Passcode':pass}, body:JSON.stringify({action:'__ping__'})})
    .then(function(r){
      if(r.status===401){ document.getElementById('loginerr').textContent='Wrong passcode.'; return; }
      document.getElementById('login').classList.add('hide');
      document.getElementById('app').classList.remove('hide');
      document.getElementById('viewlink').href = '/dashboard?p=' + encodeURIComponent(pass);
    });
}
document.getElementById('ranges').addEventListener('click', function(e){
  var b = e.target.closest('button'); if(!b) return;
  range = b.dataset.r;
  document.querySelectorAll('#ranges .chip').forEach(function(c){ c.classList.toggle('on', c===b); });
});
function run(action){
  var out = document.getElementById('out');
  out.textContent = 'Running...';
  fetch('/api/run', {method:'POST', headers:{'X-Passcode':pass}, body:JSON.stringify({
    action:action, window:range,
    notify:document.getElementById('notify').checked,
    pull_all:document.getElementById('pullall').checked
  })}).then(function(r){ return r.json(); })
    .then(function(d){ out.textContent = (d.ok ? '' : '(exit '+d.code+')\\n') + (d.output || d.error || 'done'); })
    .catch(function(){ out.textContent = 'Request failed.'; });
}
</script></body></html>"""


def main(argv=None):
    global PASSCODE
    p = argparse.ArgumentParser(description="finance-tracker control panel")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    a = p.parse_args(argv)

    if not PASSCODE:
        PASSCODE = secrets.token_urlsafe(9)
        print("No CONTROL_PANEL_PASSCODE in .env — generated a temporary one:")
        print(f"    passcode: {PASSCODE}")
        print("Set CONTROL_PANEL_PASSCODE in .env to keep it stable across restarts.\n")

    if a.host == "0.0.0.0":
        print("NOTE: binding 0.0.0.0 exposes this to your whole network. Prefer "
              "keeping it on localhost and reaching it over Tailscale (see "
              "docs/phone-access.md). The passcode is your only lock.")

    try:
        server = ThreadingHTTPServer((a.host, a.port), make_handler())
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            print(f"Port {a.port} is in use. Stop the other server or use --port {a.port + 1}.")
            return
        raise
    print(f"Control panel on http://{a.host}:{a.port}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
