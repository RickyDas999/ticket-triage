"""
Demo support tickets for teaching and testing.

Kept short on purpose — every word here is input tokens you pay for on every
click. Each sample teaches one specific rung from the Day 9 + Day 10 ladder:

Teaching rungs (from USE_CASE.md):
- "clear"              → Straightforward ticket (passes all layers on attempt 1).
- "tricky_urgent"      → Implies urgency without saying "Urgent" (Layer 2 fail, retry).
- "invalid_category"   → Fuzzy request tempting an out-of-set category (Layer 2 fail).
- "short"              → Minimal ticket; tests Layer 3 (non-echo summary).
- "mixed_bad"          → Two issues at once (billing + UI complaint).
- "urgent_not_labeled" → Emergency ticket without the word "Urgent" (retry needed).
- "very_long_summary"  → Will trigger Layer 3 (summary > 140 chars).
"""

SAMPLES = {
    "clear": (
        "Subject: Can't log in\n\n"
        "I keep getting 'Invalid credentials' even though my password is correct. "
        "Reset link never arrives either. Blocking my work — need this fixed ASAP."
    ),
    "tricky_urgent": (
        "Subject: Help needed immediately!!!\n\n"
        "Our payment system just went down. Customers can't check out and we've "
        "been down 2 hours. Revenue is on the line. Error shown: 502 Bad Gateway."
    ),
    "invalid_category": (
        "Subject: Dark mode idea\n\n"
        "Could you add a dark mode toggle to the dashboard? Some of my team works "
        "late and the bright background hurts their eyes. Is this already planned?"
    ),
    "short": (
        "Subject: No reset email\n\n"
        "Requested a password reset, no email arrived."
    ),
    "mixed_bad": (
        "Subject: Invoice looks wrong\n\n"
        "My invoice shows $149 but I'm on the $99 Premium plan — happened last "
        "month too. Also the new billing page UI is confusing."
    ),
    "urgent_not_labeled": (
        "Subject: System down RIGHT NOW\n\n"
        "We cannot process ANY transactions. This started 30 minutes ago. "
        "Customers are calling. We need immediate help or we lose clients today."
    ),
    "very_long_summary": (
        "Subject: Multiple issues\n\n"
        "Our dashboard is super slow, the login button doesn't work on mobile, "
        "the API returns wrong data, billing shows duplicate charges, dark mode "
        "is missing, and emails aren't sending. We need everything fixed now."
    ),
}


def get_sample(name: str) -> str:
    """Fetch a sample ticket by name. Returns empty string if not found."""
    return SAMPLES.get(name, "")


def list_samples() -> list[str]:
    """List all available sample ticket names."""
    return list(SAMPLES.keys())
