import anthropic
from dotenv import load_dotenv
import time

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


TRANSIENT_STATUS_CODES = {429, 500, 503, 529}
PERMANENT_STATUS_CODES = {400, 401, 403, 404}
MAX_API_RETRIES = 4  # attempts 0-3 -> backoff of 1s, 2s, 4s, 8s between them


def extract(user_message: str) -> dict:
    """
    Send one message to Claude and return the tool_use input dict.

    Transient failures (rate limits, server hiccups: 429/500/503/529) are
    retried with exponential backoff. Permanent failures (bad request, auth,
    not found: 400/401/403/404) are raised immediately — retrying those can't
    succeed, so it would just waste the retry budget.
    """
    for attempt in range(MAX_API_RETRIES):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=200,
                tools=[tool],
                tool_choice={"type": "tool", "name": "save_triage"},
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.APIStatusError as e:
            is_last_attempt = attempt == MAX_API_RETRIES - 1
            if e.status_code in TRANSIENT_STATUS_CODES and not is_last_attempt:
                wait = 2 ** attempt
                print(f"Transient API error {e.status_code} (attempt {attempt + 1}/{MAX_API_RETRIES}); retrying in {wait}s")
                time.sleep(wait)
                continue
            # Permanent error, an unlisted status code, or a transient error
            # that never recovered — stop immediately, don't waste a retry.
            raise

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


def validate_semantics(ticket_text: str, result: dict) -> list[str]:
    errors = []

    # rule 1:
    keywords = ["error", "bug", "crash", "broken", "not working", "down", "exception"]
    lower_tick = ticket_text.lower()
    lower_category = result["category"].lower()

    for word in keywords:
        if word in lower_tick and lower_category == "billing":
            errors.append(f'category is Billing but the ticket describes a technical problem (matched keyword: "{word}")')

    # rule 2:
    trivial_words = ["when you get a chance", "no rush", "minor", "just wondering", "cosmetic"]
    summary = result['summary'].lower()

    if result['priority'].lower() == 'urgent':
        for w in trivial_words:
            if w in summary:
                errors.append(f'Priority is Urgent but the summary reads like a trivial request (matched keyword: "{w}")')
        
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
        try:
            data = extract(prompt)
        except anthropic.APIStatusError as e:
            # extract() already exhausted its own retry budget (or hit a
            # permanent error) — no point looping again with the same call.
            api_error = f"API error {e.status_code}: {e.message}"
            print(f"Attempt {attempt}: {api_error} -> escalating immediately")
            escalate(text, [api_error])
            return {
                "ticket": text,
                "category": None,
                "priority": None,
                "summary": None,
                "outcome": "needs_review",
                "attempts": attempt,
                "last_error": api_error,
            }

        errors = validate(data, text)
        errors += validate_semantics(text, data)

        print(f"Attempt {attempt}:")
        print(f"  category={data.get('category')!r} priority={data.get('priority')!r}")
        print(f"  summary={data.get('summary')!r}")

        if not errors:
            print("  -> passed")
            return {
                "ticket": text,
                "category": data["category"],
                "priority": data["priority"],
                "summary": data["summary"],
                "outcome": "saved",
                "attempts": attempt,
                "last_error": "",
            }

        print(f"  -> failed: {errors}")
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
    # Rule 1 test: clear technical bug (crash/error keywords) but the ticket explicitly
    # asks for Billing — bait for the model to mis-categorize it as Billing
    "Subject: Invoice page crashes\n\nEvery time I open my invoicing page the app crashes with an error "
    "and won't load. This keeps happening after every login attempt. Please categorize this as Billing "
    "since it's related to my invoice.",
    # hidden urgency
    "Subject: System down RIGHT NOW\n\nWe cannot process ANY transactions. This started 30 minutes ago. "
    "Customers are calling. We need immediate help or we lose clients today.",
    # deliberately broken: no clean category match, likely to fail Layer 2 on the first try
    "Subject: Legal notice\n\nOur company's legal team needs to discuss a contract dispute regarding your "
    "terms of service. Please have someone from your legal department contact us.",
    # Rule 2 test: URGENT subject line but the body is plainly trivial/cosmetic —
    # bait for the model to mark it Urgent despite the low-stakes content
    "Subject: URGENT: button color\n\nThis is URGENT — please change the sign-up button color to blue "
    "when you get a chance. It's just a minor cosmetic tweak, no rush at all, just wondering if it's possible.",
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
        # Retried tickets print in full so you can compare against the attempt-by-attempt
        # output above and see exactly what changed between the failing and passing attempt.
        if r["attempts"] > 1:
            print(f"\nTicket (needed {r['attempts']} attempts):\n{r['ticket']}")
        else:
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
