#!/usr/bin/env python3
"""Measure how reliably a local SLM routes questions to finance_spend args.

This tests the RISKY part of the design (small-model tool-calling) in isolation
— no OpenClaw runtime, no Plaid needed. It calls Ollama's /api/chat directly
with the SAME enum-locked tool schema OpenClaw will use, then checks the
model's chosen {category, window} against golden expectations.

Prereqs on your Mac:
  1. Install Ollama:  https://ollama.com/download
  2. Pull a model:    ollama pull llama3.2:3b
  3. Ollama serves on http://localhost:11434 automatically.

Usage:
  python openclaw/test/test_routing.py                      # default model
  python openclaw/test/test_routing.py --model qwen2.5:3b   # compare models
  python openclaw/test/test_routing.py --repeat 3           # check consistency

Stdlib only — no pip installs.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL_JSON = HERE.parent / "tools" / "finance-spend" / "tool.json"
CASES_JSON = HERE / "routing_cases.json"

SYSTEM_PROMPT = (
    "You answer questions about the user's personal spending by calling the "
    "finance_spend tool. NEVER answer without calling it. You only choose two "
    "values: category and window, each restricted to the tool's allowed enum "
    "values. If no category is named use 'all'; if no time is named use "
    "'last_7_days'. Do not invent numbers."
)


def load_tool_schema():
    spec = json.loads(TOOL_JSON.read_text())
    # Ollama tool format: {"type":"function","function":{name,description,parameters}}
    return [{"type": "function", "function": {
        "name": spec["name"],
        "description": spec["description"],
        "parameters": spec["parameters"],
    }}]


def call_ollama(host, model, question, tools):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "tools": tools,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    req = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


# Small models often emit natural-language phrases instead of the exact enum
# (e.g. "this week" not "last_7_days"). Rather than fight that with prompting,
# we deterministically normalize synonyms -> enum. This is the "let code own
# the windows" lever: the model proposes, code maps to the allowed value.
WINDOW_SYNONYMS = {
    "today": "today", "this week": "last_7_days", "last week": "last_7_days",
    "past week": "last_7_days", "last 7 days": "last_7_days", "7 days": "last_7_days",
    "weekly": "last_7_days", "this month": "mtd", "month to date": "mtd",
    "month-to-date": "mtd", "so far this month": "mtd", "mtd": "mtd",
    "last 30 days": "last_30_days", "past 30 days": "last_30_days",
    "30 days": "last_30_days", "past month": "last_30_days",
}
CATEGORY_SYNONYMS = {
    "restaurants": "dining", "restaurant": "dining", "eating out": "dining",
    "food": "dining", "grocery": "groceries", "uber": "transport",
    "rideshare": "transport", "gas": "transport",
}


def _normalize(value, allowed, synonyms):
    v = str(value).strip().lower()
    if v in allowed:
        return v
    return synonyms.get(v, value)  # unknown -> return as-is so validation flags it


def extract_args(response):
    """Return {category, window} from the first tool call, or None."""
    msg = response.get("message", {})
    calls = msg.get("tool_calls") or []
    if not calls:
        return None
    fn = calls[0].get("function", {})
    args = fn.get("arguments")
    if isinstance(args, str):  # some builds return a JSON string
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return None
    if not isinstance(args, dict):
        return None
    cat = _normalize(args.get("category", "all"),
                     set(CATEGORY_SYNONYMS.values()) | {"all"}, CATEGORY_SYNONYMS)
    win = _normalize(args.get("window", "last_7_days"),
                     {"today", "last_7_days", "mtd", "last_30_days"}, WINDOW_SYNONYMS)
    return {"category": cat, "window": win}


def run(host, model, repeat):
    tools = load_tool_schema()
    cases = json.loads(CASES_JSON.read_text())["cases"]

    # Fail fast with a friendly message if Ollama isn't reachable.
    try:
        call_ollama(host, model, "ping", tools)
    except urllib.error.URLError as e:
        print(f"❌ Can't reach Ollama at {host} ({e}).")
        print("   Install from https://ollama.com/download, then: "
              f"ollama pull {model}")
        return 2

    total = passed = no_call = 0
    print(f"\nModel: {model}  |  cases: {len(cases)}  |  repeat: {repeat}\n")
    print(f"{'result':7} {'expected':28} {'got':28} question")
    print("-" * 100)

    for case in cases:
        exp = {"category": case["category"], "window": case["window"]}
        for _ in range(repeat):
            total += 1
            try:
                got = extract_args(call_ollama(host, model, case["q"], tools))
            except Exception as e:
                got = None
                err = str(e)[:40]
            if got is None:
                no_call += 1
                mark = "NOCALL"
                got_str = "(no tool call)"
            else:
                ok = got == exp
                passed += ok
                mark = "PASS" if ok else "FAIL"
                got_str = f"{got['category']}/{got['window']}"
            exp_str = f"{exp['category']}/{exp['window']}"
            print(f"{mark:7} {exp_str:28} {got_str:28} {case['q'][:44]}")

    pct = (passed / total * 100) if total else 0
    print("-" * 100)
    print(f"\nAccuracy: {passed}/{total} ({pct:.0f}%)   "
          f"no-tool-call: {no_call}   model: {model}")
    if pct < 90:
        print("\nTip: <90% suggests trying a stronger tool-calling model "
              "(e.g. qwen2.5:7b) or adding few-shot examples to SKILL.md.")
    return 0 if pct >= 90 else 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="http://localhost:11434")
    p.add_argument("--model", default="llama3.2:3b")
    p.add_argument("--repeat", type=int, default=1,
                   help="Run each case N times to check consistency")
    args = p.parse_args()
    sys.exit(run(args.host, args.model, args.repeat))


if __name__ == "__main__":
    main()
