import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

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

ticket = "Every time I log into the app, I am able to use it for 5 minutes until it kicks me out and I have to sign back in"

resp = client.messages.create( 
    model='claude-sonnet-5',
    max_tokens=200,
    tools=[tool],
    tool_choice= {"type": "tool", "name": "save_triage"},
    messages= [{"role": "user", "content": ticket}]
)

for block in resp.content:
    if block.type == "tool_use":
        print(block.input)