# Use Case — Support Ticket Triage (CCAF Day 9 + Day 10)

## One line
Paste a raw customer support message → get back a clean, validated
`{ category, priority, summary }` record your system can act on — or a safe
escalation when it can't.

## Why this use case
It exercises **every rung** of the Day 9 + Day 10 ladder in one honest flow, using
a scenario every learner already understands (a helpdesk inbox). No invoices, no
domain jargon, no external services.

| Ladder rung (from the deck) | Where it shows up here |
|---|---|
| Ask & pray → parse fails | Tab 1: ask for JSON in words, watch a fence/sentence break `json.loads()` |
| Force the shape (schema) | The `input_schema` for the triage tool |
| Guarantee with `tool_use` | Tab 2: strict tool call → a ready dict, no parsing |
| Check `stop_reason` | Shown on every result panel |
| Shape ≠ meaning | Tab 3: a valid record with a bad priority / empty summary |
| Validate (3 layers) | The `validate()` gate: schema (done by tool_use) → allowed-values → content |
| Retry with the reason | Tab 4: loop feeds the exact error back into the next attempt |
| Escalate, don't loop forever | Budget of 3; on failure the ticket is flagged `needs_review` |

## What it extracts
From one free-text ticket message, three fields:

- **category** — one of a fixed set: `Billing`, `Bug`, `Feature Request`,
  `Account`, `Other`
- **priority** — one of: `Low`, `Medium`, `High`, `Urgent`
- **summary** — a one-sentence plain-English summary (non-empty, ≤ 140 chars)

## The three validation layers (Day 10 core)
1. **Shape** — right fields, right types. Guaranteed by strict `tool_use`, so this
   layer never fails at runtime.
2. **Allowed values** — `category` and `priority` must be from the fixed lists. A
   model can return a tidy-but-invalid label like `"Critical"` (not in our set).
3. **Content sense** — `summary` must be non-empty and within length; must not just
   echo the raw ticket verbatim.

A record can pass layer 1 and still fail 2 or 3 — that's the whole point of Day 10.

## The retry contract
- On a validation failure, retry the extraction **with the specific reason attached**
  (e.g. `priority "Critical" is not allowed; choose from [Low, Medium, High, Urgent]`).
- Hard budget: **3 attempts**. Log every attempt.
- If still failing after the budget, **do not save** — write the ticket to a
  `needs_review` state with the last error, for a human to handle.

## Storage (simple, no MCP)
A single local **SQLite** file (`triage.db`), created automatically. One table,
`tickets`, holding the raw message, the extracted fields, the outcome
(`saved` / `needs_review`), attempts used, and a timestamp. A "History" view in the
app reads it back. A one-click **CSV export** is included. No cloud, no keys beyond
the Anthropic API key.

## What "done" looks like
- A ticket with a clear message → a saved row with sensible category/priority/summary.
- A deliberately tricky ticket (implies urgency without saying it; or nudges the model
  toward an invalid label) → visible retries that feed the reason back, then either a
  save or a clean escalation.
- The "Break it" tab can still produce a raw parse failure on demand, so the class
  sees the problem the rest of the app solves.

## Out of scope (keep it teachable)
- No auth, no multi-user, no deployment config beyond running locally.
- No MCP, no Airtable, no webhooks, no email.
- No batching (that's a later session) — one ticket at a time is the teaching unit.
