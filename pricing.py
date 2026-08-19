"""
Token counting and cost calculation for Claude models.

Prices are from the Anthropic API (as of Feb 2025).
This is a teaching tool — prices may change; refer to api.anthropic.com for current rates.
"""

# Pricing per 1M tokens (as of Feb 2025)
PRICING = {
    "claude-haiku-4-5-20251001": {
        "input": 0.80,      # $0.80 per 1M input tokens
        "output": 4.00,     # $4.00 per 1M output tokens
    },
    "claude-sonnet-5": {
        "input": 3.00,
        "output": 15.00,
    },
    "claude-opus-5": {
        "input": 15.00,
        "output": 60.00,
    },
}


def get_model_pricing(model: str) -> dict:
    """
    Get input and output pricing (per 1M tokens) for a model.
    Returns a dict with 'input' and 'output' keys.
    Falls back to Haiku pricing if model not found.
    """
    return PRICING.get(model, PRICING["claude-haiku-4-5-20251001"])


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> dict:
    """
    Calculate the cost of an API call.

    Args:
        model: The model name (e.g., "claude-haiku-4-5-20251001")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        A dict with:
        - input_cost: Cost of input tokens (in USD)
        - output_cost: Cost of output tokens (in USD)
        - total_cost: Total cost (in USD)
        - total_tokens: Total tokens used
    """
    pricing = get_model_pricing(model)

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "total_tokens": input_tokens + output_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def format_cost(cost_usd: float) -> str:
    """
    Format a cost in USD as a plain, readable dollar string.
    Kept as plain $-notation on purpose (no µ/milli symbols) — this app is
    for non-coders, and "$0.0003" is easier to trust than "$0.30 µ".
    """
    if cost_usd < 0.00005:
        return "< $0.0001"
    return f"${cost_usd:.4f}"


def format_tokens(count: int) -> str:
    """Format a token count with thousand separators."""
    return f"{count:,}"


def estimate_cost_before_call(model: str, ticket_text: str, assumed_output_tokens: int = 60) -> dict:
    """
    Rough PRE-CALL estimate, shown to the learner before they spend anything.

    We don't have a tokenizer here, so we use a simple rule of thumb:
    ~4 characters ≈ 1 token (true for English text). We also add a small
    fixed overhead for the tool schema and instructions that travel with
    every request, since those cost tokens too even though the learner
    doesn't type them.

    This is intentionally approximate — its job is to give a learner a
    "roughly how much will this cost me" number before they click, not an
    exact figure. The real, exact numbers always come from the API response
    afterward (see the 'Behind the scenes' panel).
    """
    TOOL_SCHEMA_OVERHEAD_TOKENS = 120  # the TRIAGE_TOOL definition + system framing

    ticket_tokens_est = max(10, len(ticket_text) // 4)
    input_tokens_est = ticket_tokens_est + TOOL_SCHEMA_OVERHEAD_TOKENS

    return calculate_cost(model, input_tokens_est, assumed_output_tokens)
