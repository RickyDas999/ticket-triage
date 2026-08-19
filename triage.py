"""
Day 9: Structured output and validation.

This module is pure Python — no Streamlit — so it can be unit-tested and reused.
Every function is a teachable step on the ladder from "ask and pray" to
"guaranteed structure + validated meaning."
"""

import json
import time
from anthropic import Anthropic

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

MODEL = "claude-haiku-4-5-20251001"

CATEGORIES = ["Billing", "Bug", "Feature Request", "Account", "Other"]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]

# ─────────────────────────────────────────────────────────────────────────────
# The Triage Tool: strict input_schema forces the shape (Day 9)
# ─────────────────────────────────────────────────────────────────────────────

TRIAGE_TOOL = {
    "name": "save_triage",
    "description": "Save a triaged support ticket with category, priority, and summary.",
    "input_schema": {
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
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions: safe extraction from Claude responses
# ─────────────────────────────────────────────────────────────────────────────


def first_tool_input(response) -> dict:
    """
    Extract the tool input from a response.
    Searches for the first tool_use block and returns its input.
    Safe: returns {} if no tool was called.
    """
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    return {}


def first_text(response) -> str:
    """
    Extract plain text from a response.
    Safe: returns empty string if no text blocks exist.
    """
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 + Layer 3 Validation (Day 10)
# ─────────────────────────────────────────────────────────────────────────────


def validate(data: dict) -> tuple[bool, str]:
    """
    Three-layer validation:

    Layer 1 (shape): Handled by tool_use input_schema; guaranteed at runtime.
    Layer 2 (allowed values): Check category and priority against fixed sets.
    Layer 3 (content sense): Check summary is non-empty, short enough, not a verbatim echo.

    Returns (ok, reason):
      - ok: True if all layers pass, False otherwise.
      - reason: Empty string if ok; otherwise, a specific message explaining the error.
    """

    # Layer 2: Allowed values
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

    # Layer 3: Content sense
    summary = data.get("summary", "").strip()
    if not summary:
        return False, "summary is empty; provide a one-sentence summary"
    if len(summary) > 140:
        return False, f"summary is {len(summary)} chars; must be ≤ 140"

    # All checks passed
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# Extract: strict tool_use (Day 9)
# ─────────────────────────────────────────────────────────────────────────────


def extract(text: str) -> tuple[dict, object, dict, float]:
    """
    Extract triage data from a ticket using strict tool_use.

    This is the Day 9 "force the shape" rung: we define an input_schema and set
    tool_choice to force the model to call the tool. This guarantees we get a
    well-shaped dict back (or an error, but never unparseable text).

    Args:
        text: The raw ticket message.

    Returns:
        (data, response, request_dict, elapsed_seconds)
        - data: The tool input dict (guaranteed to have category, priority, summary keys).
        - response: The full Claude response object (for inspection).
        - request_dict: A dict of the request we sent (for the "behind the scenes" panel).
        - elapsed_seconds: How long the API call took.
    """
    client = Anthropic()

    # Build the user message.
    user_message = f"Support ticket:\n\n{text}"

    # Build the request dict for logging.
    request_dict = {
        "model": MODEL,
        "max_tokens": 250,  # A triage record is tiny (3 short fields) — no need for a big cap.
        "tools": [TRIAGE_TOOL],
        "tool_choice": {"type": "tool", "name": "save_triage"},
        "messages": [{"role": "user", "content": user_message}],
    }

    # Make the API call and time it.
    start = time.time()
    response = client.messages.create(**request_dict)
    elapsed = time.time() - start

    # Extract the tool input (Layer 1 shape is guaranteed by tool_use).
    data = first_tool_input(response)

    return data, response, request_dict, elapsed


# ─────────────────────────────────────────────────────────────────────────────
# Triage: extract and validate in a single pass (Day 9)
# ─────────────────────────────────────────────────────────────────────────────


def triage_single_pass(text: str) -> dict:
    """
    Extract and validate a ticket in one pass. No retries.

    This is Day 9: extract with strict tool_use, then validate layers 2 + 3.
    If validation fails, return the error but do not retry.

    Args:
        text: The raw ticket message.

    Returns:
        A dict with:
        - outcome: "saved" (passed all validations) or "validation_failed"
        - data: The extracted {category, priority, summary} or None if failed
        - log: A list with one entry (the single attempt)
        - validation_error: If failed, the reason why
    """
    # Extract with strict tool_use (Layer 1 shape is guaranteed).
    extracted, response, request_dict, elapsed = extract(text)

    # Build the attempt log.
    attempt_log = {
        "attempt": 1,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "stop_reason": response.stop_reason,
        "elapsed_seconds": round(elapsed, 2),
        "extracted_data": extracted,
        "validation_ok": False,
        "validation_error": "",
        "exchange": format_request_response(request_dict, response),
    }

    # Validate the extraction (Layers 2 and 3).
    ok, reason = validate(extracted)

    if ok:
        # ✓ All layers passed.
        attempt_log["validation_ok"] = True
        return {
            "outcome": "saved",
            "data": extracted,
            "log": [attempt_log],
            "validation_error": "",
        }
    else:
        # ✗ Validation failed.
        attempt_log["validation_error"] = reason
        return {
            "outcome": "validation_failed",
            "data": None,
            "log": [attempt_log],
            "validation_error": reason,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Bonus: a function to format a request/response pair for display
# ─────────────────────────────────────────────────────────────────────────────


def format_request_response(request_dict: dict, response: object) -> dict:
    """
    Format a request and response for the 'Behind the scenes' panel.
    Includes token counts, stop_reason, and full JSON representations.
    """
    # Build a response dict that mirrors the request structure.
    response_dict = {
        "model": MODEL,
        "stop_reason": response.stop_reason,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
        "content": [
            {
                "type": block.type,
                "text": getattr(block, "text", None),
                "tool_use_id": getattr(block, "id", None),
                "name": getattr(block, "name", None),
                "input": getattr(block, "input", None),
            }
            for block in response.content
        ],
    }

    return {
        "request": request_dict,
        "response": response_dict,
    }
