# Architecture — Support Ticket Triage

## File layout (flat, small, teachable)
```
ticket-triage/
├── app.py              # Streamlit UI — the 4 tabs + History
├── triage.py           # core logic: extract (tool_use), validate, retry loop
├── store.py            # SQLite: init, save, list, CSV export
├── samples.py          # a handful of ready-to-paste demo tickets
├── requirements.txt    # streamlit, anthropic, python-dotenv
├── .env.example        # ANTHROPIC_API_KEY=...
└── README.md           # setup + run + what each tab teaches
```
Keep it to these files. No packages, no subfolders — a non-coder can open any file
and follow it.

## The data flow (one ticket)
```
raw ticket text
      │
      ▼
[ triage.extract() ]  ── strict tool_use, tool_choice forces the triage tool
      │                    returns block.input  → a guaranteed-shape dict
      ▼
[ triage.validate() ] ── layer 2 (allowed values) + layer 3 (content sense)
      │                    returns (ok, reason)
      ├── ok ─────────────► store.save(status="saved")  ─► History
      │
      └── not ok ─► retry with `reason` fed back ─┐
                    (up to BUDGET = 3 attempts)   │
                          │                        │
                    still failing ────────────────┘
                          ▼
                 store.save(status="needs_review", last_error=reason)
```

## Module responsibilities

### `triage.py`
- `TRIAGE_TOOL` — name `save_triage`, with `input_schema` for
  `{category, priority, summary}` and `required` = all three.
- `extract(text, prior_error="")` → calls `client.messages.create(...)` with
  `tools=[TRIAGE_TOOL]` and `tool_choice={"type":"tool","name":"save_triage"}`.
  Returns `(data, resp, request_dict, seconds)`. If `prior_error` is set, it is
  appended to the user message as an explicit correction instruction.
- `validate(data)` → returns `(ok, reason)`:
  - category in `CATEGORIES`, else reason names the bad value + the allowed set;
  - priority in `PRIORITIES`, likewise;
  - summary non-empty, ≤ 140 chars, and not a verbatim copy of the ticket.
- `run_triage(text, budget=3)` → the loop: extract → validate → retry-with-reason →
  return a result object `{outcome, data, attempts, log, last_error}` where
  `outcome` is `"saved"` or `"needs_review"`. Pure logic, no Streamlit — so it can
  be unit-tested and reused.
- Constants: `CATEGORIES`, `PRIORITIES`, `MODEL = "claude-haiku-4-5-20251001"`, `BUDGET = 3`.
- Helper `first_tool_input(resp)` and `first_text(resp)` for safe extraction.

### `store.py`
- `init_db()` — create `triage.db` and the `tickets` table if missing.
- `save(record)` — insert one row.
- `list_recent(limit=50)` — read rows back for the History tab.
- `export_csv()` — dump the table to `tickets_export.csv`, return its path.
- Table `tickets`: `id, created_at, raw_text, category, priority, summary,
  outcome, attempts, last_error`.

### `app.py`
- Loads `.env` (with `st.secrets` fallback), builds the client lazily.
- Tabs:
  1. **Break it** — naive `messages.create` asking for JSON in words, then
     `json.loads()` on the text; show success or the `JSONDecodeError`.
  2. **Triage it** — `run_triage()`; show the final record, the outcome badge,
     `stop_reason`, and save to SQLite on success.
  3. **Validate** — a radio of prepared records (good / bad-priority / empty-summary)
     run through `validate()` only, to isolate the meaning check.
  4. **Retry loop** — a tricky ticket + a budget slider; show the attempt-by-attempt
     log and the final saved/escalated outcome.
  5. **History** — `list_recent()` in a table + a "Download CSV" button.
- Every API result has a **🔍 Behind the scenes** expander: input/output tokens,
  `stop_reason`, and the raw request + response JSON.

## The three validation layers, mapped to code
| Layer | Enforced by | Fails when |
|---|---|---|
| 1 · Shape | strict `tool_use` `input_schema` | (never at runtime — guaranteed) |
| 2 · Allowed values | `validate()` set checks | category/priority not in the fixed lists |
| 3 · Content sense | `validate()` string checks | summary empty, too long, or a verbatim echo |

## Key conventions (must hold)
- Model string **`claude-haiku-4-5-20251001`** everywhere.
- `client.messages.create()` and read tool data from `block.input`; read text from
  `response.content[i].text`. **Never** OpenAI-style methods.
- **No** `temperature` parameter anywhere.
- `python-dotenv` loads `.env` automatically — the learner never `export`s.
- The retry loop **always** has a hard budget and **always** escalates on exhaustion;
  it must never return an empty/blank record silently.
