# CLAUDE.md — Support Ticket Triage (CCAF teaching build)

This is a **teaching** project for the Claude Certified Architect course, Day 9 +
Day 10 (structured output, validation, retry). Optimise every choice for
**clarity a non-coder can follow**, not cleverness.

## What this project is
A small Streamlit app that turns a raw support ticket into a clean, validated
`{ category, priority, summary }` record, with a real retry loop and safe
escalation. Storage is a local SQLite file. No MCP, no cloud, no auth.

## Golden rules (do not violate)
1. **Model string is `claude-haiku-4-5-20251001`.** Nowhere else. Never invent a different one.
2. Use the canonical Anthropic SDK only:
   - `client.messages.create(...)`
   - read tool output from `block.input` (the `tool_use` block)
   - read text from `response.content[i].text`
   - **Never** use OpenAI-style calls (`client.chat.completions.create`,
     `response.choices[0]...`).
3. **No `temperature` parameter** anywhere. It is deprecated on current models and
   returns an error. Do not add it as a "reliability" lever.
4. Force structure with **strict `tool_use`**: define a tool with an `input_schema`
   and call with `tool_choice={"type":"tool","name":...}`. Read `block.input`.
   Do **not** ask for JSON in a prompt and then `json.loads()` — except in the
   deliberate "Break it" tab, whose whole job is to show that failing.
5. The retry loop **must**: (a) feed the specific validation error back into the next
   attempt, (b) stop at a hard budget of 3, (c) escalate to `needs_review` on
   exhaustion. It must never loop forever or save a blank record.
6. `python-dotenv` loads `.env` automatically. The learner never runs `export`.
7. Keep the file list flat and small (see ARCHITECTURE.md). No extra packages,
   no framework, no subfolders.

## Validation is three layers
- Layer 1 (shape) is handled by `tool_use` — don't re-check types by hand.
- Layer 2 (allowed values): `category` ∈ fixed list, `priority` ∈ fixed list.
- Layer 3 (content sense): `summary` non-empty, ≤ 140 chars, not a verbatim echo.
- On any failure, `validate()` returns a **reason string** that is specific enough
  to guide a retry (name the bad value AND the allowed set).

## Fixed vocabularies
- `CATEGORIES = ["Billing", "Bug", "Feature Request", "Account", "Other"]`
- `PRIORITIES = ["Low", "Medium", "High", "Urgent"]`

## Code style
- Comment **why**, not just what, in plain English — a senior non-coder is reading.
- Triple-quoted multi-line strings for any long prompt text.
- Pure logic (`extract`, `validate`, `run_triage`) lives in `triage.py` with **no
  Streamlit imports**, so it can be unit-tested and read on its own.
- Small functions, obvious names. No premature abstraction.

## Behind-the-scenes panel (required)
Every live API result in the UI must offer an expander showing: input/output token
counts, `stop_reason`, and the raw request + response JSON. This is a teaching
feature — learners must be able to see what travelled to the model.

## Definition of done
- App runs with `streamlit run app.py` (and `python3 -m streamlit run app.py`).
- Opens without an API key (shows a friendly notice); works fully with one.
- All four teaching tabs behave as described in ARCHITECTURE.md, plus History + CSV.
- SQLite file is created automatically on first run.
- A tricky ticket visibly triggers retries that carry the reason forward, then either
  saves or escalates.
