# OpenClaw finance agent (constrained SLM)

Ask your finance tracker spending questions over chat (WhatsApp/Telegram/etc.)
using a **small local model**. The design keeps the SLM on a very short leash:
it only decides two enum values; all money logic stays in Python.

## How it stays reliable

The whole point is that a small model is *unreliable at open-ended tool use*,
so we remove the openness:

1. **One tool only** (`finance_spend`) — nothing else to mis-pick.
2. **Enum-locked arguments** — `category` and `window` can only be values from
   a fixed list (`tool.json`). The model can't invent "dinning".
3. **Restricted prompt** (`SKILL.md`) — "never invent numbers, always call the
   tool, only choose category + window".
4. **`temperature: 0.1` + `retry_on_parse_failure`** — near-deterministic, with
   an auto re-prompt on malformed calls.
5. **Deterministic safety net** — `index.js` re-validates args against the same
   allow-lists before running anything.
6. **All logic in Python** — the model does zero math; `spend_query.py` owns it.

## Layout

```
openclaw/
  tools/finance-spend/
    tool.json     # enum-locked schema the model must obey
    index.js      # thin shim -> shells out to Python (no logic)
  skills/finance-query/
    SKILL.md      # constrained instructions + few-shot examples
  bin/
    spend_query.py  # owns all finance logic (SKELETON — wire to src/ next)
  openclaw.config.example.json5  # local-SLM + tool-allowlist config
```

Data flow:

```
chat msg -> SLM -> finance_spend(category, window) -> index.js -> spend_query.py
                                                                      -> src/ pipeline
         <- reply (tool's summary) <-------------------------------------┘
```

## Status

- [x] Skeleton: tool schema, shim, skill, config
- [x] Wire `spend_query.py` to the real `src/` pipeline (task 2)
- [ ] Point OpenClaw at a local SLM and test routing (task 3)

`spend_query.py` now runs the real pipeline: `load_config -> resolve_window ->
fetch_all_transactions -> filter_expenses -> filter_by_category -> summarize`.

## Category mapping

Friendly enums map onto Plaid's `personal_finance_category`. Most map to a
`primary` code; `dining` and `groceries` share `FOOD_AND_DRINK` at primary, so
they split on the `detailed` code (`groceries` = `FOOD_AND_DRINK_GROCERIES`,
`dining` = everything else under food & drink).

## Quick local test (Python side, no OpenClaw needed)

```bash
# Real query (needs your .env Plaid creds):
.venv/bin/python openclaw/bin/spend_query.py --category dining --window last_7_days
# -> {"summary": "You spent $... on dining in the last 7 days ...", ...}
```

On any error (missing creds, network) it prints `{"error": "..."}` and exits
non-zero, which `index.js` surfaces to the agent instead of crashing.
