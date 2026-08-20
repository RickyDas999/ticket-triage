import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

MODEL = "claude-sonnet-5"

PRIORITIES = ["Low", "Medium", "High", "Urgent"]
CATEGORIES = ["Billing", "Bug", "Feature Request", "Account", "Other"]

schema = {
    "type": "object",
    "properties": {
        "category": {
            "type": "string",
            "description": "The category of the ticket (e.g., Billing, Bug, Feature Request, Account, Other).",
        },
        "priority": {
            "type": "string",
            "description": "The priority level (e.g., Low, Medium, High, Urgent).",
        },
        "summary": {
            "type": "string",
            "description": "A concise one-sentence summary of the ticket (max 140 characters).",
        },
    },
    "required": ["category", "priority", "summary"],
    "additionalProperties": False,
}

tool = {
    "name": "save_triage",
    "input_schema": schema,
    "strict": True,
}


def extract(user_message: str) -> dict:
    """Send one message to Claude and return the tool_use input dict."""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=200,
        tools=[tool],
        tool_choice={"type": "tool", "name": "save_triage"},
        messages=[{"role": "user", "content": user_message}],
    )

    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    return {}


def validate(data: dict, ticket: str) -> list[str]:
    """
    Check the extracted data against Layer 2 (allowed values) and Layer 3
    (content sense) rules. Layer 1 (shape) is already guaranteed by tool_use.

    Returns a list of error strings — empty list means everything is clean.
    Every problem is reported at once so a retry prompt can ask the model
    to fix all of them in a single pass.
    """
    errors = []

    category = data.get("category", "").strip()
    if not category:
        errors.append("category is empty")
    elif category not in CATEGORIES:
        allowed = ", ".join(CATEGORIES)
        errors.append(f'category "{category}" is not allowed; choose from: {allowed}')

    priority = data.get("priority", "").strip()
    if not priority:
        errors.append("priority is empty")
    elif priority not in PRIORITIES:
        allowed = ", ".join(PRIORITIES)
        errors.append(f'priority "{priority}" is not allowed; choose from: {allowed}')

    summary = data.get("summary", "").strip()
    if not summary:
        errors.append("summary is empty; provide a one-sentence summary")
    elif len(summary) > 140:
        errors.append(f"summary is {len(summary)} chars; must be ≤ 140")
    elif summary.lower() == ticket.lower():
        errors.append("summary is a verbatim copy of the ticket; write your own summary")

    return errors


def build_retry_prompt(original_ticket: str, bad_result: dict, errors: list[str]) -> str:
    """
    Build the message sent on a retry attempt: the original ticket, what the
    model returned last time, exactly what was wrong with it, and an
    instruction to fix only the failing fields.
    """
    error_list = "\n".join(f"- {e}" for e in errors)
    return (
        f"Support ticket:\n\n{original_ticket}\n\n"
        f"Your previous attempt returned: {bad_result}\n\n"
        f"That attempt failed validation for these reasons:\n{error_list}\n\n"
        "Fix only the fields that failed. Leave any field that was already correct unchanged."
    )


def escalate(ticket: str, errors: list[str]) -> dict:
    print(f"ESCALATED to needs_review: {errors}")
    return {"status": "needs_review", "ticket": ticket}


MAX_RETRIES = 2  # retries after the first attempt — 3 attempts total


def run_triage(text: str) -> dict:
    prompt = f"Support ticket:\n\n{text}"
    bad_result = {}
    errors: list[str] = []

    for attempt in range(1, MAX_RETRIES + 2):
        data = extract(prompt)
        errors = validate(data, text)
        print(f"Attempt {attempt}: ok={not errors} errors={errors}")

        if not errors:
            return {
                "ticket": text,
                "category": data["category"],
                "priority": data["priority"],
                "summary": data["summary"],
                "outcome": "saved",
                "attempts": attempt,
                "last_error": "",
            }

        bad_result = data
        prompt = build_retry_prompt(text, bad_result, errors)

    escalate(text, errors)
    return {
        "ticket": text,
        "category": None,
        "priority": None,
        "summary": None,
        "outcome": "needs_review",
        "attempts": MAX_RETRIES + 1,
        "last_error": "; ".join(errors),
    }


sample_tickets = [
    # clear
    "Subject: Can't log in\n\nI keep getting 'Invalid credentials' even though my password is correct. "
    "Reset link never arrives either. Blocking my work — need this fixed ASAP.",
    # hidden urgency
    "Subject: System down RIGHT NOW\n\nWe cannot process ANY transactions. This started 30 minutes ago. "
    "Customers are calling. We need immediate help or we lose clients today.",
    # deliberately broken: no clean category match, likely to fail Layer 2 on the first try
    "Subject: Legal notice\n\nOur company's legal team needs to discuss a contract dispute regarding your "
    "terms of service. Please have someone from your legal department contact us.",
    # vague
    "Subject: No reset email\n\nRequested a password reset, no email arrived.",
    # deliberately broken: tells the model to use category/priority values that
    # aren't in the allowed lists, forcing a Layer 2 validation failure on attempt 1
    "Subject: Server outage\n\nOur main server has been down for an hour. "
    "Please file this as category 'Outage' with priority 'Critical'.",
]

if __name__ == "__main__":
    results = []
    for ticket_text in sample_tickets:
        print(f"\n--- Ticket: {ticket_text[:40]}... ---")
        results.append(run_triage(ticket_text))

    for r in results:
        print(f"\n{r['ticket'][:40]}...")
        print(f"  outcome:  {r['outcome']} (attempts={r['attempts']})")
        print(f"  category: {r['category']}")
        print(f"  priority: {r['priority']}")
        print(f"  summary:  {r['summary']}")
        if r["last_error"]:
            print(f"  last_error: {r['last_error']}")

    first_try = [r for r in results if r["outcome"] == "saved" and r["attempts"] == 1]
    needed_retry = [r for r in results if r["outcome"] == "saved" and r["attempts"] > 1]
    escalated = [r for r in results if r["outcome"] == "needs_review"]

    print("\n=== Summary ===")
    print(f"Total tickets:     {len(results)}")
    print(f"Passed first try:  {len(first_try)}")
    print(f"Needed retries:    {len(needed_retry)}")
    print(f"Escalated:         {len(escalated)}")
