"""Human-in-the-loop tool: ask_user.

The LLM can call this tool mid-execution to ask the user a question and
get their input. Supports:
- multi-choice: list of options, user picks one (or types custom)
- free-text: user types a free-form answer

Returns the user's answer to the LLM. The conversation continues with
the LLM having the user's input.
"""
from __future__ import annotations

import json
import sys


def ask_user(
    question: str,
    options: list[str] | None = None,
    default: str | None = None,
    timeout_s: int = 0,
) -> str:
    """Ask the user a question and return their answer.

    Use this whenever you need human judgment, clarification, or a decision
    you cannot make alone. Examples:
    - "I found 3 hypotheses. Which should I test first?"
    - "The field data says X but the local parameter is Y. Which to use?"
    - "This change would break backward compatibility. Proceed anyway?"
    - "Should I add a new scorer (D15) or modify an existing one?"

    Args:
        question: The question to ask the user. Be specific and include
            the context needed to make a decision.
        options: Optional list of choices. If provided, user can pick one
            (by number or text) or type a custom answer.
        default: Default answer if user just presses Enter (no input).
        timeout_s: If > 0, auto-resolve with default after this many seconds.
            If 0 (default), block until user responds.

    Returns:
        JSON string with {"question", "answer", "options"} so the LLM
        can use the answer in its next step.
    """
    print("\n" + "═" * 70, file=sys.stderr)
    print("🤔 AGENT ASKS:", file=sys.stderr)
    print(f"   {question}", file=sys.stderr)
    print("═" * 70, file=sys.stderr)

    if options:
        for i, opt in enumerate(options, 1):
            print(f"   {i}. {opt}", file=sys.stderr)
        print("   (or type your own answer)", file=sys.stderr)

    if default:
        print(f"   [default: {default}]", file=sys.stderr)

    try:
        if timeout_s > 0:
            import select
            print("   > ", end="", file=sys.stderr, flush=True)
            ready, _, _ = select.select([sys.stdin], [], [], timeout_s)
            if ready:
                answer = sys.stdin.readline().strip()
            else:
                print(f"(timeout → default: {default})", file=sys.stderr)
                answer = default or ""
        else:
            answer = input("   > ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n   (interrupted → using default)", file=sys.stderr)
        answer = default or ""

    if not answer:
        answer = default or ""

    # Resolve answer to option if numeric choice
    resolved = answer
    if options:
        try:
            idx = int(answer) - 1
            if 0 <= idx < len(options):
                resolved = options[idx]
        except ValueError:
            # User typed the option text directly — that's fine
            resolved = answer

    print(f"   → {resolved}", file=sys.stderr)
    print("═" * 70 + "\n", file=sys.stderr)

    return json.dumps({
        "question": question,
        "answer": resolved,
        "options": options,
    })