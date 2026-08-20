#!/usr/bin/env python3
"""
Daily Kite login for a PERSONAL desktop setup.

THE CONSTRAINT: access_token expires every trading day and there is no refresh
token. Kite's docs give the personal-app answer -- register 127.0.0.1 as the
redirect_url host and run a local web server to catch the redirect.

Flow: open browser -> you log in -> Kite redirects to 127.0.0.1 with
request_token -> we exchange it for access_token -> cache it for the day.

One browser interaction each morning. Everything else is scripted.

DO NOT try to automate the login itself with stored TOTP secrets. That is a
grey area against Zerodha's terms and it puts your 2FA seed on disk. At a few
trades a day you are at the terminal anyway.

    pip install kiteconnect
    export KITE_API_KEY=... KITE_API_SECRET=...
    python3 tools/auth.py
"""
import datetime as dt
import http.server
import json
import os
import pathlib
import threading
import urllib.parse
import webbrowser

PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}/"     # register EXACTLY this as redirect_url
CACHE = pathlib.Path(__file__).resolve().parent.parent / ".kite_session.json"


def cached_token():
    """Today's token, or None. Tokens die at the next trading day."""
    if not CACHE.exists():
        return None
    try:
        blob = json.loads(CACHE.read_text())
    except json.JSONDecodeError:
        return None                      # corrupt cache is not fatal, just re-login
    if blob.get("date") != dt.date.today().isoformat():
        return None
    return blob.get("access_token")


def _capture_request_token(api_key):
    """Serve 127.0.0.1 until Kite redirects back with a request_token."""
    holder = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            holder.update({k: v[0] for k, v in q.items()})
            ok = "request_token" in holder
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h2>Token captured. Close this tab.</h2>" if ok else
                b"<h2>No request_token in the redirect.</h2>")
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        def log_message(self, *a):       # keep the console clean
            pass

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"https://kite.zerodha.com/connect/login?api_key={api_key}&v=3"
    print(f"Opening {url}")
    print(f"Waiting on {REDIRECT} …")
    webbrowser.open(url)
    server.serve_forever()
    server.server_close()

    if "request_token" not in holder:
        raise RuntimeError(f"login did not return a request_token: {holder}")
    return holder["request_token"]


def login(force=False):
    """Return a valid access_token, reusing today's cached one unless force."""
    if not force:
        tok = cached_token()
        if tok:
            print("Reusing today's cached token.")
            return tok

    api_key = os.environ.get("KITE_API_KEY")
    api_secret = os.environ.get("KITE_API_SECRET")
    if not (api_key and api_secret):
        raise SystemExit("Set KITE_API_KEY and KITE_API_SECRET (see .env.example).")

    from kiteconnect import KiteConnect
    kite = KiteConnect(api_key=api_key)
    request_token = _capture_request_token(api_key)
    session = kite.generate_session(request_token, api_secret=api_secret)
    access_token = session["access_token"]

    CACHE.write_text(json.dumps(
        {"date": dt.date.today().isoformat(), "access_token": access_token}))
    CACHE.chmod(0o600)                   # it is a credential; treat it like one
    print(f"Logged in as {session.get('user_name', '?')}. Token cached until tomorrow.")
    return access_token


if __name__ == "__main__":
    token = login()
    print(f"\nexport KITE_ACCESS_TOKEN={token}")
