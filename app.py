"""
Support Ticket Triage: Interactive Teaching App.

Design goal: a non-coder should be able to see, on one screen, per click:
  1. The exact text + JSON we sent Claude.
  2. The exact JSON Claude sent back.
  3. Whether it passed validation, and why (in plain English).
  4. Exactly what it cost.

No information is hidden behind nested tabs — everything above is always
visible right under the button you clicked. Raw JSON is available in
expanders for anyone who wants to inspect the wire format, but you never
*have* to open them to understand what happened.

Note on styling: we use Streamlit's NATIVE st.info/st.success/st.error boxes
everywhere, not custom HTML/CSS. Streamlit's native boxes automatically pick
readable text/background colors for both light and dark themes; hand-rolled
HTML with a hardcoded background color does not, and turns invisible in dark
mode (light-blue box + light text = unreadable). Never hardcode colors here.
"""

import json
import streamlit as st
from dotenv import load_dotenv
from anthropic import Anthropic

import triage
import store
import samples
import pricing

load_dotenv()

# Initialize database on app startup (so it exists even if nothing is saved yet)
store.init_db()

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="🎫 Ticket Triage",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎫 Support Ticket Triage")
st.caption("Day 9 — structured output and validation. Every API call shown in full, in plain English.")

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar: running cost — simple, not a dashboard
# ─────────────────────────────────────────────────────────────────────────────

if "total_cost" not in st.session_state:
    st.session_state.total_cost = 0.0
    st.session_state.total_calls = 0
    st.session_state.total_input_tokens = 0
    st.session_state.total_output_tokens = 0

with st.sidebar:
    st.subheader("💰 This session")
    st.metric("Total spent", pricing.format_cost(st.session_state.total_cost))
    st.caption(
        f"{st.session_state.total_calls} API calls · "
        f"{pricing.format_tokens(st.session_state.total_input_tokens)} in / "
        f"{pricing.format_tokens(st.session_state.total_output_tokens)} out tokens"
    )
    st.divider()
    st.caption(f"**Model:** `{triage.MODEL}`")
    model_price = pricing.get_model_pricing(triage.MODEL)
    st.caption(f"${model_price['input']}/M input · ${model_price['output']}/M output tokens")
    st.caption("Haiku is Anthropic's cheapest, fastest model — built for exactly this kind of small, structured task.")


def _track_cost(input_tokens: int, output_tokens: int):
    """Add one API call's tokens/cost to the running session total."""
    st.session_state.total_calls += 1
    st.session_state.total_input_tokens += input_tokens
    st.session_state.total_output_tokens += output_tokens
    st.session_state.total_cost += pricing.calculate_cost(
        triage.MODEL, input_tokens, output_tokens
    )["total_cost"]


def check_api_key() -> bool:
    try:
        Anthropic()
        return True
    except Exception:
        st.error("❌ No API key found. Add `ANTHROPIC_API_KEY` to your `.env` file, then refresh.")
        return False


def cost_estimate_line(ticket_text: str):
    """Show a rough 'this will cost about X' line BEFORE the learner spends anything."""
    est = pricing.estimate_cost_before_call(triage.MODEL, ticket_text)
    st.caption(f"💡 Estimated cost for this click: ~{pricing.format_cost(est['total_cost'])} (rough, before Claude replies)")


# ─────────────────────────────────────────────────────────────────────────────
# THE core reusable panel: what we sent → what came back → cost
# (Validation pass/fail is rendered separately by each tab, right after this.)
# ─────────────────────────────────────────────────────────────────────────────


def render_exchange(request_dict: dict, response_dict: dict, extracted_data: dict,
                     input_tokens: int, output_tokens: int, stop_reason: str,
                     elapsed_seconds: float, heading: str = "Behind the scenes",
                     raw_text: str = ""):
    """
    Render one API call in full, always visible, plain language first:

    Step 1 — the exact text we sent (+ raw JSON in an expander)
    Step 2 — the exact fields Claude sent back (+ raw JSON in an expander)
    A cost/tokens caption line.

    Works for BOTH the naive text-prompt flow (Tab 1) and the tool_use flow
    (Tabs 2/4) — the caller just passes plain dicts, already-serializable.
    """
    st.markdown(f"##### 🔍 {heading}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📤 Step 1 — What we sent Claude**")
        user_text = request_dict["messages"][0]["content"]
        st.text_area(
            "Message text sent",
            value=user_text,
            height=140,
            disabled=True,
            label_visibility="collapsed",
            key=f"req_text_{id(request_dict)}_{input_tokens}_{output_tokens}",
        )
        with st.expander("📄 See the exact raw request JSON"):
            st.code(json.dumps(request_dict, indent=2), language="json")

    with col2:
        st.markdown("**📥 Step 2 — What Claude sent back**")
        if extracted_data:
            st.write(f"**Category:** {extracted_data.get('category', '—')}")
            st.write(f"**Priority:** {extracted_data.get('priority', '—')}")
            st.write(f"**Summary:** {extracted_data.get('summary', '—')}")
        elif raw_text:
            # Tab 1 has no structured fields to show — only loose text. Showing it
            # verbatim is the whole lesson: you can SEE the ``` fence that breaks
            # json.loads(), instead of just being told parsing failed.
            st.caption("Claude replied with **plain text**, not structured fields. Here it is, byte for byte:")
            st.code(raw_text, language="text")
        else:
            st.write("*(no structured tool data — see raw response)*")
        with st.expander("📄 See the exact raw response JSON"):
            st.code(json.dumps(response_dict, indent=2), language="json")

    cost = pricing.calculate_cost(triage.MODEL, input_tokens, output_tokens)
    st.caption(
        f"🔢 {input_tokens} input + {output_tokens} output tokens "
        f"→ **{pricing.format_cost(cost['total_cost'])}** · "
        f"stop_reason: `{stop_reason}`" + (f" · {elapsed_seconds}s" if elapsed_seconds else "")
    )


def render_exchange_from_attempt(attempt_log: dict, heading: str = "Behind the scenes"):
    """Convenience wrapper: unpack a triage attempt log and render it."""
    exchange = attempt_log["exchange"]
    render_exchange(
        request_dict=exchange["request"],
        response_dict=exchange["response"],
        extracted_data=attempt_log["extracted_data"],
        input_tokens=attempt_log["input_tokens"],
        output_tokens=attempt_log["output_tokens"],
        stop_reason=attempt_log["stop_reason"],
        elapsed_seconds=attempt_log["elapsed_seconds"],
        heading=heading,
    )


def render_validation(attempt_log: dict):
    """Step 3 — plain pass/fail box with the specific reason. Uses native st boxes."""
    st.markdown("**✅ Step 3 — Did it pass validation?**")
    if attempt_log["validation_ok"]:
        st.success(
            "**Passed.** Category and priority are on our allowed lists, "
            "and the summary is a real, short, non-empty sentence."
        )
    else:
        st.error(f"**Failed:** {attempt_log['validation_error']}")


# ─────────────────────────────────────────────────────────────────────────────
# Tab 1: Break it — the OLD way, without tool_use
# ─────────────────────────────────────────────────────────────────────────────


def tab_break_it():
    st.header("1️⃣ Break it — the old way (no tool_use)")
    st.info(
        "This tab deliberately **does not** use tool_use. We just ask Claude for JSON "
        "inside a sentence, then run Python's `json.loads()` on whatever text comes back. "
        "If the reply isn't pure, parseable JSON — a stray sentence, a code fence, anything "
        "— this crashes. Tab 2 fixes this permanently with tool_use."
    )

    if not check_api_key():
        return

    # The text area's content lives in session state under "break_it_ticket".
    # Seed it once with a sample so the box is never empty on first load.
    if "break_it_ticket" not in st.session_state:
        st.session_state.break_it_ticket = samples.get_sample("clear")

    col_ticket, col_samples = st.columns([3, 1])

    # IMPORTANT: the sample buttons are written BEFORE the text area in code.
    # Streamlit refuses to let you change a widget's session-state value after
    # that widget has been created in the same run, so the button must get its
    # write in first. The column layout still puts the buttons on the right.
    with col_samples:
        st.markdown("**📋 Try these:**")

        # Map samples to what they teach
        sample_lessons = {
            "clear": "✅ Passes all layers",
            "tricky_urgent": "🔄 Tricky case",
            "invalid_category": "⚠️ Bad category",
            "short": "📝 Short message",
            "mixed_bad": "📌 Multiple issues",
            "urgent_not_labeled": "🚨 Implies urgency",
            "very_long_summary": "📄 Too long",
        }

        for name in samples.list_samples():
            lesson = sample_lessons.get(name, "Sample")
            if st.button(f"{lesson}\n`{name}`", key=f"break_sample_{name}", use_container_width=True):
                st.session_state.break_it_ticket = samples.get_sample(name)
                st.rerun()

    with col_ticket:
        # No value= here on purpose: the key alone drives the content, so the
        # sample buttons above can replace the text without fighting Streamlit.
        ticket = st.text_area("Raw ticket:", height=120, key="break_it_ticket")

    cost_estimate_line(ticket)

    if st.button("🔴 Try to extract (the fragile way)", key="break_it_btn", use_container_width=True):
        client = Anthropic()
        prompt = (
            "Extract the category, priority, and summary from this support ticket.\n"
            "Return ONLY a JSON object with keys: category, priority, summary.\n\n"
            f"Ticket:\n{ticket}\n\nJSON:"
        )
        request_dict = {"model": triage.MODEL, "max_tokens": 150, "messages": [{"role": "user", "content": prompt}]}

        with st.spinner("Calling Claude..."):
            response = client.messages.create(**request_dict)
        _track_cost(response.usage.input_tokens, response.usage.output_tokens)

        text = triage.first_text(response)

        # Try to parse — this is the step that crashes, and that is the POINT.
        # We deliberately do NOT clean the text first. In real life Claude almost
        # always wraps JSON in a markdown fence (```json ... ```), and raw
        # json.loads() dies on the very first backtick. Every "just strip the
        # fence" patch is a guess about a format nobody promised us. Tab 2 shows
        # the real fix: tool_use, where the shape is guaranteed, not hoped for.
        parsed_data = None
        parse_error = ""
        try:
            parsed_data = json.loads(text)
        except json.JSONDecodeError as e:
            parse_error = str(e)

        # Build a serializable response dict, same shape as Tabs 2/4 use, so
        # this tab gets the identical "behind the scenes" treatment.
        response_dict = {
            "model": triage.MODEL,
            "stop_reason": response.stop_reason,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            "content": [
                {"type": block.type, "text": getattr(block, "text", None)}
                for block in response.content
            ],
        }

        st.divider()
        render_exchange(
            request_dict=request_dict,
            response_dict=response_dict,
            extracted_data=parsed_data,  # None if parsing failed — shown honestly below
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason,
            elapsed_seconds=0,
            raw_text=text,
        )

        st.markdown("**🧪 Step 3 — Can Python actually read it?**")
        st.caption("We run `json.loads(claude_reply)` on the text above — nothing else, no cleanup.")

        if parsed_data is None:
            # THE teaching moment. Name the crash, then show the exact first
            # characters Python choked on so it is concrete, not abstract.
            st.error(
                f"❌ **Invalid JSON — `json.loads()` crashed.**\n\n"
                f"Python's error: `{parse_error}`"
            )

            first_line = text.split("\n", 1)[0]
            st.markdown("**Why it crashed — look at the very first line Claude sent:**")
            st.code(first_line or "(empty reply)", language="text")

            if text.lstrip().startswith("```"):
                st.warning(
                    "That opening ` ``` ` is a **markdown code fence**. To a human it looks like "
                    "decoration around the JSON. To `json.loads()` it is a syntax error on character 1 — "
                    "it expected `{` and got a backtick, so it never reached the actual data."
                )

            st.info(
                "**Could we just strip the fence?** We could — and it would work until the day Claude "
                "writes `Here's the JSON:` first, or adds a trailing note, or uses a different fence. "
                "Every patch is a guess about a format nobody guaranteed. "
                "**Tab 2 removes the guessing:** `tool_use` returns a real Python dict, so there is no "
                "text to parse and nothing to break."
            )

            st.markdown("**And notice what we never even got to check:**")
            st.caption(
                "Layers 2 and 3 (allowed values, sensible summary) never ran — parsing failed first, "
                "so we have no data to validate at all."
            )
        else:
            # Rare, but possible: Claude sometimes returns bare JSON with no fence.
            # Parsing passing is NOT the finish line — the values can still be junk.
            st.success("✅ **Valid JSON** — `json.loads()` parsed it this time. But that only proves the *shape*.")

            ok, reason = triage.validate(parsed_data)

            st.markdown("**Now the meaning — Layers 2 & 3:**")
            if ok:
                st.success(f"✅ **Passed.** Category, priority and summary are all usable. {reason}".strip())
            else:
                st.error(
                    f"❌ **Failed:** {reason}\n\n"
                    "Parseable ≠ correct. Claude invented a value that isn't on our list. "
                    "Tab 2 catches this every time."
                )

            st.markdown("**What was extracted:**")
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Category:** `{parsed_data.get('category', '—')}`")
            col2.write(f"**Priority:** `{parsed_data.get('priority', '—')}`")
            summary = str(parsed_data.get("summary", "—"))
            col3.write(f"**Summary:** `{summary[:40] + '…' if len(summary) > 40 else summary}`")


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2: Triage it — the real pipeline
# ─────────────────────────────────────────────────────────────────────────────


def tab_triage_it():
    st.header("2️⃣ Triage it — extract, validate, save")

    # The text area's content lives in session state under "triage_it_ticket".
    # Seed it once with a sample so the box is never empty on first load.
    if "triage_it_ticket" not in st.session_state:
        st.session_state.triage_it_ticket = samples.get_sample("clear")

    # Show the three layers explicitly
    st.subheader("🛡️ The Three Layers of Validation")
    layer_col1, layer_col2, layer_col3 = st.columns(3)
    with layer_col1:
        st.info(
            "**Layer 1: Shape**\n\n"
            "Tool_use with `input_schema` guarantees JSON is always well-formed.\n\n"
            "✅ Always passes (SDK enforces it)"
        )
    with layer_col2:
        st.info(
            "**Layer 2: Allowed Values**\n\n"
            "Category ∈ {Billing, Bug, Feature, Account, Other}\n\n"
            "Priority ∈ {Low, Medium, High, Urgent}"
        )
    with layer_col3:
        st.info(
            "**Layer 3: Content Sense**\n\n"
            "Summary must be:\n"
            "- Non-empty\n"
            "- ≤ 140 chars\n"
            "- Not a verbatim echo"
        )

    st.divider()
    st.subheader("📊 How Validation Works")

    # Show what each layer catches
    with st.expander("🔍 See what each layer catches (example failures)"):
        ex_col1, ex_col2, ex_col3 = st.columns(3)
        with ex_col1:
            st.markdown("**Layer 1: Shape**")
            st.error("JSON malformed (e.g., missing quotes)")
            st.caption("❌ `json.loads()` crashes\n✅ tool_use prevents this")
        with ex_col2:
            st.markdown("**Layer 2: Allowed Values**")
            st.error('priority: "Critical" ← not in {Low, Medium, High, Urgent}')
            st.caption("❌ Caught by validation\n✅ Error shown to user")
        with ex_col3:
            st.markdown("**Layer 3: Content Sense**")
            st.error("summary: \"\" (empty) or > 140 chars")
            st.caption("❌ Caught by validation\n✅ Error shown to user")

    st.divider()
    st.markdown("**👇 Try a ticket below — watch each layer in action:**")
    st.divider()

    # Email field (optional) — for tracking who submitted each ticket
    email = st.text_input("📧 Your email (optional):", placeholder="your@email.com", key="triage_email")

    col_ticket, col_samples = st.columns([3, 1])

    # Buttons first in code (see the same note in tab_break_it): a widget's
    # session-state value can only be changed before that widget is created.
    with col_samples:
        st.markdown("**📋 Try these:**")

        # Map samples to what they teach
        sample_lessons = {
            "clear": "✅ Passes all layers",
            "tricky_urgent": "🔄 Tricky case",
            "invalid_category": "⚠️ Bad category",
            "short": "📝 Short message",
            "mixed_bad": "📌 Multiple issues",
            "urgent_not_labeled": "🚨 Implies urgency",
            "very_long_summary": "📄 Too long",
        }

        for name in samples.list_samples():
            lesson = sample_lessons.get(name, "Sample")
            if st.button(f"{lesson}\n`{name}`", key=f"triage_sample_{name}", use_container_width=True):
                st.session_state.triage_it_ticket = samples.get_sample(name)
                st.rerun()

    with col_ticket:
        # Key only, no value= — the sample buttons above own the content.
        ticket = st.text_area("Raw ticket:", height=130, key="triage_it_ticket")

    if not check_api_key():
        return

    cost_estimate_line(ticket)

    if st.button("✅ Extract & validate", key="triage_it_btn", use_container_width=True):
        with st.spinner("Calling Claude..."):
            result = triage.triage_single_pass(ticket)

        # Track the cost of this single attempt
        _track_cost(result["log"][0]["input_tokens"], result["log"][0]["output_tokens"])

        st.divider()
        outcome_col, cost_col = st.columns(2)
        outcome_col.metric("Outcome", "✅ Saved" if result["outcome"] == "saved" else "❌ Validation failed")
        run_cost = pricing.calculate_cost(triage.MODEL, result["log"][0]["input_tokens"], result["log"][0]["output_tokens"])["total_cost"]
        cost_col.metric("Cost for this ticket", pricing.format_cost(run_cost))

        # Show the single attempt
        attempt_log = result["log"][0]
        st.divider()
        render_exchange_from_attempt(attempt_log)
        render_validation(attempt_log)

        st.divider()
        st.markdown("#### 💾 Automatic Save to Database")

        if result["outcome"] == "saved" and result["data"]:
            # Auto-save successful tickets
            row_id = store.save({
                "email": email,
                "raw_text": ticket,
                "category": result["data"].get("category"),
                "priority": result["data"].get("priority"),
                "summary": result["data"].get("summary"),
                "outcome": "saved",
                "attempts": 1,
                "last_error": "",
            })
            st.success(
                f"✅ **Auto-saved!** Row #{row_id} is now in your History tab. "
                f"Go to Tab 4 to see it."
            )
        else:
            # If validation failed, still save for review
            row_id = store.save({
                "email": email,
                "raw_text": ticket,
                "category": None,
                "priority": None,
                "summary": None,
                "outcome": "validation_failed",
                "attempts": 1,
                "last_error": result["validation_error"],
            })
            st.error(
                f"❌ **Validation failed:** {result['validation_error']}\n\n"
                f"✅ **Auto-saved as row #{row_id}** for your review. "
                f"See it in Tab 4 History."
            )


# ─────────────────────────────────────────────────────────────────────────────
# Tab 3: Validate — layers 2 & 3 in isolation, no API call, no cost
# ─────────────────────────────────────────────────────────────────────────────


def tab_validate():
    st.header("3️⃣ Validate — check meaning, not shape")
    st.info(
        "No API call here, no cost — this tab runs the `validate()` function directly "
        "on pre-made records so you can see all three layers in isolation. "
        "Layer 1 (shape) never fails here — tool_use already guarantees it."
    )

    # Comprehensive test cases covering all three layers and edge cases
    test_records = {
        "✅ Valid — all layers pass": {
            "category": "Bug",
            "priority": "High",
            "summary": "Login page crashes with special characters in the password."
        },
        "❌ Layer 2 — Invalid priority 'Critical'": {
            "category": "Bug",
            "priority": "Critical",
            "summary": "Login page crashes."
        },
        "❌ Layer 2 — Invalid category 'Feedback'": {
            "category": "Feedback",
            "priority": "Medium",
            "summary": "Dark mode would be nice."
        },
        "❌ Layer 3 — Empty summary": {
            "category": "Feature Request",
            "priority": "Low",
            "summary": ""
        },
        "❌ Layer 3 — Summary too long (>140)": {
            "category": "Billing",
            "priority": "Medium",
            "summary": "Our invoice shows wrong amount. Also the UI is confusing. Also the dashboard is slow. Also we need dark mode. Also the API returns errors." * 2
        },
        "❌ Layer 3 — Verbatim echo (not paraphrased)": {
            "category": "Account",
            "priority": "Low",
            "summary": "Requested a password reset, no email arrived."  # This is just copying the raw input, not a summary
        },
    }

    selected = st.selectbox("Pick a test record:", list(test_records.keys()))
    record = test_records[selected]

    st.markdown("**Record:**")
    col1, col2, col3 = st.columns(3)
    col1.write(f"**Category:** `{record['category']}`")
    col2.write(f"**Priority:** `{record['priority']}`")
    col3.write(f"**Summary:** `{record['summary'][:50] + '...' if len(record['summary']) > 50 else record['summary'] or '(empty)'}`")

    st.divider()
    ok, reason = triage.validate(record)
    if ok:
        st.success("✅ **Passed all validation layers.**\n\nThis record is ready to save.")
    else:
        st.error(f"❌ **Failed:** {reason}")


# ─────────────────────────────────────────────────────────────────────────────
# Tab 4: History
# ─────────────────────────────────────────────────────────────────────────────


def tab_history():
    st.header("📊 History")
    st.info(
        "All tickets you save in Tab 2 appear here. "
        "The database file (`triage.db`) is in your project folder and persists across sessions."
    )

    stats = store.get_db_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total tickets", stats["total_tickets"])
    c2.metric("Saved", stats["saved"])
    c3.metric("Needs review", stats["needs_review"])

    st.divider()
    rows = store.list_recent(limit=100)
    if rows:
        st.markdown("#### Recent tickets (newest first):")

        # Table headers
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 2, 1.5, 1.5, 3, 1.5, 1, 1])
        col1.write("**ID**")
        col2.write("**Email**")
        col3.write("**Created**")
        col4.write("**Category**")
        col5.write("**Summary**")
        col6.write("**Outcome**")
        col7.write("**Attempts**")
        col8.write("**Delete**")

        st.divider()

        # Table rows
        for r in rows:
            col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 2, 1.5, 1.5, 3, 1.5, 1, 1])
            col1.write(str(r["id"]))
            col2.write(r.get("email") or "—")
            col3.write(r["created_at"][:16])
            col4.write(r["category"] or "—")
            col5.write((r["summary"] or "—")[:50])
            col6.write("✅ Saved" if r["outcome"] == "saved" else "⚠️ Review")
            col7.write(str(r["attempts"]))

            # Delete button
            if col8.button("🗑️", key=f"delete_{r['id']}", help=f"Delete ticket #{r['id']}"):
                store.delete_ticket(r["id"])
                st.rerun()

        st.divider()
        if st.button("⬇️ Download as CSV", use_container_width=True):
            csv_path = store.export_csv()
            with open(csv_path, "r", encoding="utf-8") as f:
                st.download_button("📥 Click to download", data=f.read(), file_name="tickets_export.csv", mime="text/csv", use_container_width=True)
    else:
        st.info(
            "📭 **No tickets yet.** \n\n"
            "1. Go to Tab 2 ('Triage it')\n"
            "2. Click one of the sample buttons or enter your own ticket\n"
            "3. Click '✅ Extract & validate'\n"
            "4. Watch it auto-save (no extra button needed!)\n"
            "5. Come back here to see your ticket"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Day 9 only: Break it, Triage it, Validate, History (no retry loop)
    tab1, tab2, tab3, tab4 = st.tabs(["🔴 Break it", "✅ Triage it", "🔍 Validate", "📊 History"])
    with tab1:
        tab_break_it()
    with tab2:
        tab_triage_it()
    with tab3:
        tab_validate()
    with tab4:
        tab_history()
