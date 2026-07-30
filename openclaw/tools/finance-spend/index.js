// finance_spend — OpenClaw custom tool
//
// Thin JS shim: the LLM/SLM only ever produces { category, window } (both
// enum-locked by tool.json). This shim forwards them to the Python entrypoint
// that owns ALL finance logic. The model does no math and picks no free-form
// values — that is the whole constraint strategy.

import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// openclaw/tools/finance-spend/ -> repo root is three levels up.
const REPO_ROOT = path.resolve(__dirname, "..", "..", "..");
const PYTHON = process.env.FINANCE_PYTHON || path.join(REPO_ROOT, ".venv", "bin", "python");
const ENTRYPOINT = path.join(REPO_ROOT, "openclaw", "bin", "spend_query.py");

// Defensive allow-lists that MIRROR tool.json. Even if a model somehow emits
// an out-of-enum value, we reject deterministically here rather than passing
// junk to Python. This is the "safety net under the model".
const CATEGORIES = new Set([
  "all", "dining", "groceries", "travel", "transport", "shopping",
  "entertainment", "bills_utilities", "medical", "personal_care",
]);
const WINDOWS = new Set(["today", "last_7_days", "mtd", "last_30_days"]);

// Small models emit phrases ("this week") instead of enums ("last_7_days").
// Normalize synonyms -> enum before validating, so the model's job shrinks to
// "roughly right" and code guarantees a valid value. Keep in sync with
// test/test_routing.py.
const WINDOW_SYNONYMS = {
  "today": "today", "this week": "last_7_days", "last week": "last_7_days",
  "past week": "last_7_days", "last 7 days": "last_7_days", "7 days": "last_7_days",
  "weekly": "last_7_days", "this month": "mtd", "month to date": "mtd",
  "month-to-date": "mtd", "so far this month": "mtd", "mtd": "mtd",
  "last 30 days": "last_30_days", "past 30 days": "last_30_days",
  "30 days": "last_30_days", "past month": "last_30_days",
};
const CATEGORY_SYNONYMS = {
  "restaurants": "dining", "restaurant": "dining", "eating out": "dining",
  "food": "dining", "grocery": "groceries", "uber": "transport",
  "rideshare": "transport", "gas": "transport",
};

function normalize(value, allowed, synonyms) {
  const v = String(value).trim().toLowerCase();
  if (allowed.has(v)) return v;
  return synonyms[v] ?? value;
}

export default async function run({ category = "all", window = "last_7_days" } = {}) {
  category = normalize(category, CATEGORIES, CATEGORY_SYNONYMS);
  window = normalize(window, WINDOWS, WINDOW_SYNONYMS);

  if (!CATEGORIES.has(category)) {
    return { error: `Unknown category '${category}'. Allowed: ${[...CATEGORIES].join(", ")}` };
  }
  if (!WINDOWS.has(window)) {
    return { error: `Unknown window '${window}'. Allowed: ${[...WINDOWS].join(", ")}` };
  }

  return await new Promise((resolve) => {
    const proc = spawn(PYTHON, [ENTRYPOINT, "--category", category, "--window", window], {
      cwd: REPO_ROOT,
    });

    let out = "";
    let err = "";
    proc.stdout.on("data", (d) => (out += d));
    proc.stderr.on("data", (d) => (err += d));

    proc.on("error", (e) => resolve({ error: `Failed to launch Python: ${e.message}` }));
    proc.on("close", (code) => {
      if (code !== 0) {
        return resolve({ error: `Query failed (exit ${code}): ${err.trim().slice(0, 300)}` });
      }
      // Python prints a JSON object: { "summary": "...", "total": 0.0, ... }
      try {
        resolve(JSON.parse(out));
      } catch {
        resolve({ summary: out.trim() }); // tolerate plain-text output
      }
    });
  });
}
