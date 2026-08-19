# Guide for Instructors — Support Ticket Triage App (Day 9)

## Quick Setup (5 minutes)

```bash
pip install -r requirements.txt
# Add .env file with ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```

## The Four Teaching Tabs (Today's class)

### Tab 1: "Break it" — Old way (5–10 min)
**Goal:** Show why naive JSON parsing fails

**Demo:**
1. Click "clear" sample
2. Click "🔴 Try to extract (the fragile way)"
3. Show: Step 1 (request), Step 2 (response), Step 3 (json.loads passes/fails)
4. Point: "Claude can add text. json.loads() crashes. This is the fragility."

### Tab 2: "Triage it" — New way with tool_use (15–20 min)
**Goal:** Show tool_use guarantees shape, but validation checks meaning

**Demo:**
1. Point out **three colored boxes** at top (the three layers)
2. Load "clear" sample → click "✅ Extract & validate"
3. Show: Outcome, Attempts, Cost
4. Show: Behind the scenes panel for each attempt (request → response → validation)
5. Point: "Step 2 always shows clean fields. No parsing error like Tab 1."

**Hard samples to try:**
- "tricky_urgent" — implies urgency but says "Critical" (invalid priority) → needs retry
- "invalid_category" — fuzzy request tempts wrong category
- "very_long_summary" — Claude tries to list everything (too long)

### Tab 3: "Validate" — Layers 2 & 3 in isolation (5–10 min)
**Goal:** Show validation rules without API calls

**Demo:**
1. Dropdown: try "Valid record" (passes), "Invalid priority" (fails), "Empty summary" (fails), "Too long" (fails)
2. Each shows exact error message
3. Point: "These are the rules. When Claude breaks them, we feed the error back."

### Tab 4: "History" — Persistence (2–5 min)
**Goal:** Show tickets are saved to database

**Demo:**
1. After triage in Tab 2, ticket auto-saves
2. Go to Tab 5 "History"
3. Show table, metrics, CSV export
4. Point: "Every ticket persists. You can analyze, export, audit."

---

## Auto-Save Feature (Day 9 change)

**Before:** Manual "Save" button after triage  
**Now:** Tickets auto-save when they pass validation, or auto-flag as "needs_review" if budget exhausted

**Why?** Simpler flow. Learners see result → ticket is immediately in database → they see it in History.

---

## Tab 4 "Retry loop" (Hidden for Day 9)

Tab 4 is hidden from the UI today. It will be revealed on Day 10 to teach:
- How errors are fed back
- How Claude self-corrects
- Safe escalation when budget exhausted

---

## Teaching Arc (50–70 minutes)

1. **Rungs 1–2** (Tab 1, 10 min): Show parsing failure
2. **Rungs 3–5** (Tab 2, 20 min): Tool_use guarantees shape, validation checks meaning
3. **Rung 5** (Tab 3, 10 min): Validation in isolation
4. **Q&A** (Tab 2, 10 min): Try different samples, watch them auto-save
5. **Persistence** (Tab 5, 5 min): See history, export CSV

---

## Sample Tickets & Their Purpose

| Sample | Tests | Expected |
|--------|-------|----------|
| clear | Happy path | Passes immediately |
| tricky_urgent | Implication (not explicit "Urgent") | May hint at retry pattern |
| invalid_category | Fuzzy category label | Wrong choice (teaching point for Layer 2) |
| short | Non-echo summary | Claude paraphrases (not verbatim) |
| mixed_bad | Multiple issues | Reduces to single priority |
| urgent_not_labeled | Emergency without "Urgent" | Another implication test |
| very_long_summary | Long summaries | Tests Layer 3 (length) |

---

## Key Moments

### Moment 1: "Parsing is fragile"
Show Tab 1 failure, then Tab 2 success.
> "Tab 1 crashed. Tab 2 never crashes. Why? Tool_use forces Claude to call a tool. The SDK guarantees the shape. We can't change this."

### Moment 2: "Meaning is separate"
Show Tab 3, click "Invalid priority".
> "This JSON is valid (right format). But priority 'Critical' isn't on our list. Same shape, different meaning. That's why we validate."

### Moment 3: "Rules are explicit"
Point to the three colored boxes in Tab 2.
> "Layer 1: Shape (guaranteed by tool_use). Layer 2: Allowed values (category/priority lists). Layer 3: Content sense (non-empty, short, not echo). Each layer catches different problems."

---

## Checklist Before Class

- [ ] `.env` file created with valid API key
- [ ] `pip install -r requirements.txt` done
- [ ] `streamlit run app.py` launches
- [ ] Tab 1 visible (Break it)
- [ ] Tab 2 visible (Triage it)
- [ ] Tab 3 visible (Validate)
- [ ] Tab 4 **hidden** (Retry — for Day 10)
- [ ] Tab 5 visible (History)
- [ ] Can load samples (clear, tricky_urgent, etc.)
- [ ] Can see "Behind the scenes" panel

---

## FAQ

**Q: Why does Tab 1 sometimes succeed?**  
A: If Claude returns pure JSON, it works. But that's fragile — not guaranteed. Tab 2 guarantees it.

**Q: Can I see the retry tab?**  
A: It's hidden for today (Day 9). It will be revealed tomorrow (Day 10) to teach retries and escalation.

**Q: Do I have to click "Save"?**  
A: No! Tickets auto-save when they pass validation. Go to Tab 5 to see them.

**Q: Where is the database?**  
A: `triage.db` in the project folder. SQLite format. Open with any SQLite browser.

**Q: Can learners see the code?**  
A: Yes. `triage.py` has pure logic (no Streamlit). But the app is designed so they don't need to read code — everything is visible in the GUI.

---

## After Class

- Give learners the **README.md** (how to run, database schema, common questions)
- Give learners the **TEACHING_CASES.md** (every rung explained, sample purpose)
- Optional: Show **triage.py** (pure Python, unit-testable, simple)

---

Good luck! 🎯
