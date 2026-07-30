# Running the control panel from your phone

The control panel (`scripts/control_panel.py`) is a small web page whose buttons
run the same scripts you'd type in the terminal — reports, dashboard rebuilds.
Your Mac does the work; the phone is just a remote.

You'll reach it over **Tailscale**, a private network between your own devices.
Nothing is exposed to the public internet, and it works on cellular too.

Three things stay true no matter what:

- Your Mac has to be **on and awake** for the panel to respond.
- A **passcode** guards every action — set a strong one.
- Traffic only ever flows between your own devices on your tailnet.

---

## 1. Set a passcode

Add a line to `.env` (it's gitignored, so it never leaves your Mac):

```
CONTROL_PANEL_PASSCODE=pick-something-long-and-unguessable
```

If you skip this, the panel generates a temporary passcode and prints it at
startup — fine for a quick test, but set your own so it survives restarts.

## 2. Start the panel

```
cd ~/dev/finance-tracker/finance-tracker
.venv/bin/python scripts/control_panel.py
```

It serves on `http://localhost:8000`. Open that in your Mac's browser first to
confirm it works before going to the phone.

## 3. Install Tailscale on both devices

- Mac: download from https://tailscale.com/download, install, sign in.
- Phone: install the Tailscale app from the App Store / Play Store, sign in
  with the **same account**.

That's what makes them a private network. You can confirm the Mac is on it with:

```
tailscale status
```

## 4. Expose the panel over Tailscale

With the panel running (step 2), in another terminal:

```
tailscale serve --bg 8000
```

This publishes `localhost:8000` to *your tailnet only*, over HTTPS. It prints a
URL like:

```
https://your-macs-name.your-tailnet.ts.net
```

To stop sharing later: `tailscale serve --https=443 off`.

## 5. Open it on your phone

On the phone (Tailscale connected), open that `https://…ts.net` URL in the
browser, enter your passcode, and you're in. Use Share → **Add to Home Screen**
to get an app-like icon.

---

## Keeping it available

`control_panel.py` only responds while it's running and the Mac is awake. Options:

- Simplest: leave the terminal running, and set your Mac to not sleep while
  plugged in (System Settings → Battery/Lock Screen).
- Hands-off: run it under launchd like the daily job already does. Ask me and
  I'll add a launch agent so it starts on login and restarts if it crashes.

## Security notes

- The passcode is the lock on the door — treat it like a password, and don't
  reuse your other passwords.
- Don't run the panel with `--host 0.0.0.0` unless you specifically want it on
  your local Wi-Fi; with Tailscale you don't need to. Keep it on localhost and
  let `tailscale serve` handle the private exposure.
- This panel can trigger runs and send push alerts. It does **not** expose your
  Plaid tokens or `.env` — those stay server-side.

## What the buttons do

| Button | Runs |
|--------|------|
| Run report (with the date + toggles) | `python -m src.main --window <range> [--pull-all] [--no-notify]` |
| Rebuild dashboard | `python scripts/generate_dashboard.py` |
| Open dashboard | Serves the freshly built `dashboard.html` |

Adding a new account isn't in the phone panel yet — that flow needs the browser
popup on your Mac. Run `scripts/add_account.py` there when you link a bank.
