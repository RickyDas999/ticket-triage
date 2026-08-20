import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

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
        "strict": True        
    }

ticket = "Subject: Legal notice\n\nOur company's legal team needs to discuss a contract dispute regarding your terms of service. Please have someone from your legal department contact us."

def extract(text: str, prior_error: str="") -> dict:
    user_message = f"Support ticket: \n\n{text}"
    if prior_error:
        user_message += f"\n\nYour previous attempt failed: {prior_error}\nFix this and try again."

        
    resp = client.messages.create( 
        model='claude-sonnet-5',
        max_tokens=200,
        tools=[tool],
        tool_choice= {"type": "tool", "name": "save_triage"},
        messages= [{"role": "user", "content": user_message}]
    )

    for block in resp.content:
        if block.type == "tool_use":
            data = block.input

    return data

def validate(data: dict, ticket: str) -> tuple[bool, str]:

    category = data.get("category", "").strip()
    if not category:
        return False, "category is empty"
    if category not in CATEGORIES:
        allowed = ", ".join(CATEGORIES)
        return False, f'category "{category}" is not allowed; choose from: {allowed}'

    priority = data.get("priority", "").strip()
    if not priority:
        return False, "priority is empty"
    if priority not in PRIORITIES:
        allowed = ", ".join(PRIORITIES)
        return False, f'priority "{priority}" is not allowed; choose from: {allowed}'

    summary = data.get("summary", "").strip()
    if not summary:
        return False, "summary is empty; provide a one-sentence summary"
    if len(summary) > 140:
        return False, f"summary is {len(summary)} chars; must be ≤ 140"
    if summary.lower() == ticket.lower():
        return False, "summary is a verbatim copy of the ticket; write your own summary"
    
    # All checks passed
    return True, ""

def escalate(ticket: str, reason: str) -> dict:
    print(f"ESCALATED to needs_review: {reason}")
    return {"status": "needs_review", "ticket": ticket}

def run_triage(text: str) -> dict:
    prior_error = ""
    for attempt in range(3):
        data = extract(text, prior_error)
        ok, reason = validate(data, text)
        print(f"Attempt {attempt + 1}: ok={ok} reason={reason!r}")

        if ok:
            return {
                "ticket": text,
                "category": data["category"],
                "priority": data["priority"],
                "summary": data["summary"],
                "outcome": "saved",
                "attempts": attempt + 1,
                "last_error": "",
            }
        prior_error = reason
    else:
        escalate(text, prior_error)
        return {
            "ticket": text,
            "category": None,
            "priority": None,
            "summary": None,
            "outcome": "needs_review",
            "attempts": 3,
            "last_error": prior_error,
        }


sample_tickets = [
    # clear
    "Subject: Can't log in\n\nI keep getting 'Invalid credentials' even though my password is correct. "
    "Reset link never arrives either. Blocking my work — need this fixed ASAP.",
    # hidden urgency
    "Subject: System down RIGHT NOW\n\nWe cannot process ANY transactions. This started 30 minutes ago. "
    "Customers are calling. We need immediate help or we lose clients today.",
    # out-of-set category
    "Subject: Legal notice\n\nOur company's legal team needs to discuss a contract dispute regarding your "
    "terms of service. Please have someone from your legal department contact us.",
    # vague
    "Subject: No reset email\n\nRequested a password reset, no email arrived.",
]

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

needs_review = [r for r in results if r["outcome"] == "needs_review"]

first_try = [r for r in results if r["outcome"] == "saved" and r["attempts"] == 1]
needed_retry = [r for r in results if r["outcome"] == "saved" and r["attempts"] > 1]
escalated = [r for r in results if r["outcome"] == "needs_review"]

print("\n=== Summary ===")
print(f"Total tickets:     {len(results)}")
print(f"Passed first try:  {len(first_try)}")
print(f"Needed retries:    {len(needed_retry)}")
print(f"Escalated:         {len(escalated)}")
