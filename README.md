# 🎫 Support Ticket Triage — Day 9 + Day 10 Teaching App

A small, transparent Streamlit app that triages support tickets using Claude's structured output, validation, and retry logic. **Every API call is shown in full, in plain English — nothing hidden.**

## What it demonstrates

### Day 9: Structured Output
- **Tab 1 "Break it"** — Shows the old way: ask Claude for JSON, run `json.loads()`. Fragile and fails often.
- **Tab 2 "Triage it"** — Shows the new way: force Claude to call a `tool` with an `input_schema`. Guaranteed well-formed shape.

### Day 10: Validation & Retry
Three layers of validation:
1. **Layer 1 (Shape)** — Guaranteed by tool_use; never malformed JSON.
2. **Layer 2 (Allowed values)** — Category and priority must be on fixed lists.
3. **Layer 3 (Content sense)** — Summary must be non-empty, ≤ 140 chars, not a verbatim echo.

When validation fails, the exact error is fed back into the next attempt. Hard budget of 3 attempts; if exhausted, escalate to `needs_review` for a human.

### Tab 3: Validation
Test the validation logic in isolation (no API call, no cost).

### Tab 4: Retry Loop
Watch a tricky ticket fail on attempt 1, self-correct on attempt 2.

### Tab 5: History
All saved tickets appear here. Database is a local SQLite file (`triage.db`) that persists across sessions.

---

## Three types of output you see in the GUI

### 1. **Old version (Tab 1 — "Break it")**
- **Step 1**: The exact text we sent to Claude (message text area).
- **Step 2**: The exact reply (raw text).
- **Step 3**: Did `json.loads()` parse it? (Success/Failure box).
- Shows **why this breaks** — Claude can include explanatory text, code fences, or formatting that aren't valid JSON.

### 2. **Using the AI model with tool_use (Tab 2 — "Triage it")**
- **Step 1**: The exact text we sent to Claude (message text area).
- **Step 2**: The exact structured fields Claude extracted (category, priority, summary — always well-formed).
- **Step 3**: Did the fields pass validation? (Allowed values check, content sense check).
- Shows **why tool_use is safe** — shape is guaranteed; only meaning is checked.

### 3. **Validation (Tab 3 — "Validate")**
- No API call, no cost — just runs the validation function on pre-made records.
- Shows what Layer 2 and Layer 3 catch.
- Layer 1 (shape) is never tested here because tool_use already guarantees it.

---

## Quick start

1. **Create `.env` file** with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**:
   ```bash
   streamlit run app.py
   ```

4. **Open in browser** (usually `http://localhost:8501`).

---

## Database

- **File**: `triage.db` (created automatically on first run, in the project folder).
- **Table**: `tickets` with columns:
  - `id` — Auto-incremented row ID
  - `created_at` — ISO timestamp
  - `raw_text` — Original ticket message
  - `category`, `priority`, `summary` — Extracted fields (or NULL if escalated)
  - `outcome` — "saved" or "needs_review"
  - `attempts` — How many retry attempts were made
  - `last_error` — Final validation error (if escalated)

- **Persists across sessions** — once you save a ticket, it stays in the database.

---

## How to save a ticket

1. Go to **Tab 2 "Triage it"**.
2. Enter a ticket (or load a sample).
3. Click **"✅ Extract & validate"**.
4. If all layers pass, click **"💾 Save to History"**.
5. Go to **Tab 5 "History"** to see it.

If validation fails, Claude retries with the error fed back. If it exhausts the budget (default 3), you can still save it as `needs_review` for a human.

---

## What each tab teaches

| Tab | Teaches | API calls | Cost |
|-----|---------|-----------|------|
| **1 Break it** | Why naive JSON parsing fails | 1 per click | Small |
| **2 Triage it** | How tool_use + validation + retry work | 1–3 per click (retries) | Small |
| **3 Validate** | What each validation layer catches | 0 | Free |
| **4 Retry loop** | Watch self-correction in action | 1–5 per click (configurable budget) | Small |
| **5 History** | Where saved tickets live | 0 | Free |

---

## Model and pricing

- **Model**: `claude-haiku-4-5-20251001` (Anthropic's smallest, fastest, cheapest model).
- **Pricing**: ~$0.80/M input tokens, ~$4.00/M output tokens.
- **Token estimate**: A triage ticket uses ~150–200 tokens per attempt.
- **Every call shows cost** in the UI (you can always see what you''re spending).

---

## Code structure

- **`triage.py`** — Core logic (extract, validate, retry loop). **No Streamlit imports** — pure Python, testable.
- **`store.py`** — SQLite storage. No ORM, just plain SQL anyone can read.
- **`pricing.py`** — Token counting and cost calculation.
- **`samples.py`** — Demo tickets (short, intentional, for teaching).
- **`app.py`** — Streamlit UI (5 tabs).
- **`.env`** — Your API key (you create this, `.gitignore` prevents committing it).

---

## Behind the scenes in every tab

**Every API call shows three things:**
1. **Request** — The exact text and JSON we sent to Claude (in a text area + expander).
2. **Response** — The exact fields Claude sent back (fields + expander for raw JSON).
3. **Cost** — Token counts, cost in USD, and `stop_reason`.

You **never** have to open the raw JSON expanders if you don''t want to — the plain English above is always visible.

---

## For learners

- You don''t need to read the code to understand what happened — the GUI shows everything.
- If something looks wrong, check the "Step 1" message and "Step 2" response — they''re always visible.
- Tokens and cost are always shown, so you can see exactly what you''re spending.
- The validation rules are fixed and explicit — no hidden magic.

---

## Common questions

**Q: My ticket didn''t save to History.**  
A: Make sure you clicked "✅ Extract & validate" first, then "💾 Save to History". History only shows tickets you''ve explicitly saved.

**Q: How do I see saved tickets?**  
A: Go to Tab 5 "History". It shows all tickets in the database, newest first.

**Q: What if validation fails 3 times?**  
A: The app offers to save it as `needs_review` — the raw ticket and the final error are stored, flagging it for a human to review.

**Q: Can I change the retry budget?**  
A: In Tab 4, there''s a slider. Default is 3; you can set it to 1–5.

**Q: Where''s the database file?**  
A: `triage.db` in your project folder (same folder as `app.py`). It''s a standard SQLite file — you can open it with any SQLite browser.

---

## License & credits

Teaching app for the Claude Certified Architect course, Day 9 + Day 10.  
Uses the Anthropic Python SDK with structured output and tool_use.
