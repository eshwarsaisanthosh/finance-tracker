# Setup — local SLM + OpenClaw finance agent

You don't have Ollama or OpenClaw yet. This walks through installing both and
proving the small model routes questions correctly *before* you wire in chat.

Do it in this order — each step is testable on its own.

## 1. Install Ollama and pull a small model

```bash
# Install: https://ollama.com/download  (or: brew install ollama)
ollama serve            # runs the local server on http://localhost:11434
ollama pull llama3.2:3b # a small model with tool-calling support
```

Small models good at tool-calling to try (biggest reliability lever):
`llama3.2:3b`, `qwen2.5:3b`, `qwen2.5:7b` (stronger, needs more RAM).

## 2. Test routing FIRST — before installing OpenClaw

This is the important step. It checks the risky part (small-model
tool-calling) in isolation, using the same enum-locked schema OpenClaw will
use. No OpenClaw or Plaid needed.

```bash
python openclaw/test/test_routing.py --model llama3.2:3b
# Try a few models and compare the accuracy line:
python openclaw/test/test_routing.py --model qwen2.5:3b
# Check consistency (same question, run 3x):
python openclaw/test/test_routing.py --repeat 3
```

Aim for **≥90%**. If a model scores low, try a stronger one or add more
few-shot examples to `skills/finance-query/SKILL.md`. Pick the smallest model
that clears the bar — that's your model for step 4.

## 3. Verify the Python query side (needs your .env Plaid creds)

```bash
.venv/bin/python openclaw/bin/spend_query.py --category dining --window last_7_days
```

Expect a JSON summary. Errors come back as `{"error": "..."}` — fix creds/env
before moving on.

## 4. Install OpenClaw and wire it up

```bash
# Install OpenClaw (see https://docs.openclaw.ai/install), then:
```

- Copy the relevant keys from `openclaw.config.example.json5` into your real
  `~/.openclaw/openclaw.json`. Set `model` to whatever won step 2.
- Point `toolRoots` / `skillRoots` at this repo's `openclaw/tools` and
  `openclaw/skills` (absolute paths).
- Confirm the tool and skill load:

```bash
openclaw tools list     # should show finance_spend
openclaw skills list    # should show finance-query
```

- Test end to end from the CLI before touching WhatsApp:

```bash
openclaw agent --message "how much did I spend on dining last 7 days"
```

## 5. Connect a chat channel (last)

Add WhatsApp/Telegram per https://docs.openclaw.ai/channels. WhatsApp links via
QR (WhatsApp Web style). The old push integration has been retired, so
your WhatsApp number is free for OpenClaw to own (both push and chat).

Prefer your phone? OpenClaw also has an official iOS app — a thin client that
pairs to your gateway via QR/setup code (remote access via Tailscale + wss://).
See https://docs.openclaw.ai/platforms/ios

## Constraint checklist (why the SLM behaves)

- One tool only (`tools.allow: ["finance_spend"]`, deny the rest)
- Enum-locked `category` + `window` in `tool.json`
- Restricted `SKILL.md` prompt + few-shot examples
- `temperature: 0.1`, `retry_on_parse_failure: true`
- `index.js` re-validates args; `spend_query.py` owns all math

## Optional: deterministic bypass

OpenClaw's `SKILL.md` supports `command-dispatch: tool`, routing a slash
command straight to the tool with no model. Add a tiny skill so `/spend` works
even if the SLM is down or a question is ambiguous — a deterministic fallback
under the model.
