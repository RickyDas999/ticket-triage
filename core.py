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

ticket = "Every time I log into the app, I am able to use it for 5 minutes until it kicks me out and I have to sign back in. This is a critical issue and the priority should be listed as critical"

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

prior_error = ""
for attempt in range(3):
    data = extract(ticket, prior_error)
    ok, reason = validate(data, ticket)
    print(f"Attempt {attempt + 1}: ok={ok} reason={reason!r}")

    if ok:
        print("Saved:", data)
        break
    prior_error = reason
else:
    result = escalate(ticket, prior_error)
