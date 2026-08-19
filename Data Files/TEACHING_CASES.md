# TEACHING_CASES.md — All Day 9 + Day 10 Scenarios Covered

Every rung of the Day 9 + Day 10 ladder is demonstrated with real tickets.

## The Seven Rungs

### Rung 1: "Ask & pray" → parse fails
**Where:** Tab 1 "Break it" — Shows naive JSON parsing failure

### Rung 2: "Force the shape" with schema
**Where:** triage.py TRIAGE_TOOL — Schema defined with three required fields

### Rung 3: "Guarantee with tool_use"
**Where:** Tab 2 "Triage it" — Tool_use forces Claude to call the tool, guarantees shape

### Rung 4: "Check stop_reason"
**Where:** Every tab — Caption line shows stop_reason on every result

### Rung 5: "Shape ≠ meaning"
**Where:** Tab 3 "Validate" — Well-formed JSON can still be wrong

### Rung 6: "Validate & retry"
**Where:** Tab 2 on retry (next day class in Tab 4) — Error fed back guides self-correction

### Rung 7: "Escalate safely"
**Where:** Tab 2 when budget exhausted — Flags for needs_review, never loops forever

## Sample Tickets

| Sample | Teaches | Expected |
|--------|---------|----------|
| clear | Happy path | Passes all layers |
| tricky_urgent | Retry needed | Fails → retries → passes |
| invalid_category | Invalid label | Validation catches it |
| short | Non-echo summary | Paraphrases input |
| mixed_bad | Multiple issues | Summarizes to one priority |
| urgent_not_labeled | Emergency implication | Needs retry to correct priority |
| very_long_summary | Layer 3 length check | Needs retry to shorten |

## Key Teaching Points

1. Naive JSON parsing is fragile (Tab 1)
2. Tool_use guarantees shape, not meaning (Tab 2)
3. Validation catches invalid values (Tab 3)
4. Errors guide retries (next day)
5. Safe escalation beats infinite loops (next day)
