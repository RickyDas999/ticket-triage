# Claude Code Build Prompt — Support Ticket Triage

Paste everything below the line into Claude Code, in an empty folder that also
contains `CLAUDE.md`, `USE_CASE.md`, and `ARCHITECTURE.md`. Claude Code will read
those for the rules and structure; this prompt tells it what to build.

---

Build a small **Streamlit teaching app** called **Support Ticket Triage**. First
read `CLAUDE.md`, `USE_CASE.md`, and `ARCHITECTURE.md` in this folder and follow
them exactly — especially the golden rules (model `claude-haiku-4-5-20251001`, strict
`tool_use`, no `temperature`, hard retry budget with escalation).

This app is for teaching Day 9 + Day 10 of an AI course to **non-coders**. Optimise
for readability. Comment *why* in plain English.

## What it does
Turn a raw customer support message into a clean, validated record:
`{ category, priority, summary }`. Then validate the *meaning*, retry with the
reason on failure, and escalate safely if it still fails. Save results to a local
SQLite file. No MCP, no cloud.

## Fixed vocabularies
- categories: Billing, Bug, Feature Request, Account, Other
- priorities: Low, Medium, High, Urgent

## Build these files (flat, no subfolders)
`app.py`, `triage.py`, `store.py`, `samples.py`, `requirements.txt`,
`.env.example`, `README.md`.

### triage.py (pure logic, NO streamlit imports)
- `CATEGORIES`, `PRIORITIES`, `MODEL = "claude-haiku-4-5-20251001"`, `BUDGET = 3`.
- `TRIAGE_TOOL`: a tool named `save_triage` whose `input_schema` requires
  `category` (string), `priority` (string), `summary` (string).
- `first_text(resp)` and `first_tool_input(resp)` helpers.
- `extract(text, prior_error="")`: call
  `client.messages.create(model=MODEL, max_tokens=400, tools=[TRIAGE_TOOL],
  tool_choice={"type":"tool","name":"save_triage"}, messages=[...])`.
  If `prior_error` is non-empty, append a clear correction instruction to the user
  message that names the error and the allowed values. Return
  `(data, resp, request_dict, seconds)`.
- `validate(data)` → `(ok, reason)`:
  - category not in CATEGORIES → reason names the value and the allowed set;
  - priority not in PRIORITIES → same;
  - summary empty, > 140 chars, or equal to the raw ticket → reason explains.
- `run_triage(text, budget=BUDGET)`: loop extract → validate → retry-with-reason;
  return `{"outcome": "saved" | "needs_review", "data":..., "attempts": n,
  "log": [...per attempt...], "last_error":...}`. Never loop past the budget;
  never return a blank record.

### store.py (SQLite, no ORM)
- `init_db()` creates `triage.db` + table `tickets(id, created_at, raw_text,
  category, priority, summary, outcome, attempts, last_error)`.
- `save(record)`, `list_recent(limit=50)`, `export_csv()` → returns a CSV path.

### samples.py
A list of 5–6 demo tickets as plain strings, including:
- a clear one (easy),
- one whose tone hides urgency ("no rush, but our checkout has been down all day"),
- one likely to tempt an out-of-set label (so retries trigger),
- one that's vague/short (so the summary check matters).

### app.py (Streamlit UI)
- Load `.env` with `load_dotenv()`, plus an `st.secrets` fallback for cloud. Build
  the Anthropic client lazily so the app opens with no key (show a friendly notice).
- A text area prefilled from `samples.py` (a picker to swap samples).
- Five tabs:
  1. **Break it** — naive: ask for JSON in words, `resp.content[0].text`, then
     `json.loads()`. Show the raw reply and either the parsed dict or the
     `JSONDecodeError`. This tab is meant to sometimes fail — that's the lesson.
  2. **Triage it** — run `run_triage()`; show the final record, an outcome badge
     (✅ saved / ⛔ needs review), `stop_reason`, and on success call `store.save`.
  3. **Validate** — a radio of prepared records (good / invalid priority / empty
     summary) passed through `validate()` only, to isolate layer 2 + 3.
  4. **Retry loop** — a tricky ticket + a budget slider; render the attempt-by-attempt
     log (each attempt's data + PASS/FAIL + reason), then the final outcome.
  5. **History** — `list_recent()` as a table + a "Download CSV" button.
- Every live API result gets a **🔍 Behind the scenes** expander: input/output
  tokens, `stop_reason`, and the raw request + response JSON.

## Requirements & docs
- `requirements.txt`: streamlit, anthropic, python-dotenv.
- `.env.example`: `ANTHROPIC_API_KEY=sk-ant-...` and an optional `CCAF_MODEL`.
- `README.md`: setup (`pip install -r requirements.txt`, `cp .env.example .env`),
  run (`streamlit run app.py`, and the `python3 -m streamlit run app.py` fallback),
  and a short "what each tab teaches" section.

## Verify before you finish
1. `python3 -c "import ast; ast.parse(open('triage.py').read())"` (and for app.py) —
   no syntax errors.
2. Unit-test `validate()` on three hand-made dicts (good, invalid priority, empty
   summary) and print the results.
3. Boot headless once to confirm it serves without crashing:
   `python3 -m streamlit run app.py --server.headless true --server.port 8600`,
   check it responds, then stop it.
4. Confirm `triage.db` is created on first save and `export_csv()` writes a file.

Keep it small, correct, and readable. When done, print a short "how to run" summary
and list the files you created.
