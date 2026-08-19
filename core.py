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

resp = client.messages.create( 
    model='claude-sonnet-5',
    max_tokens=200,
    tools=[tool],
    tool_choice= {"type": "tool", "name": "save_triage"},
    messages= [{"role": "user", "content": ticket}]
)

def validate(data: dict) -> tuple[bool, str]:

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

    # All checks passed
    return True, ""



for block in resp.content:
    if block.type == "tool_use":
        data = block.input
        print(block.input)

ok, reason = validate(data)
print(ok, reason)

