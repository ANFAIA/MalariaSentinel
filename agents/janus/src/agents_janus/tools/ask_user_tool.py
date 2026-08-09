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
import os
import sys


def _safe_write(text: str, file=None) -> None:
    """Write text to a file handle, falling back to stdout if closed.

    DeepAgents/LangChain may close stderr via thread cleanup or broken
    HTTP streams. This wrapper prevents ValueError('I/O operation on
    closed file') from crashing the tool.
    """
    target = file or sys.stderr
    try:
        target.write(text)
        target.flush()
    except (ValueError, OSError):
        try:
            sys.stdout.write(text)
            sys.stdout.flush()
        except Exception:
            pass


def _safe_print(*args, **kwargs) -> None:
    """Print with stderr fallback."""
    try:
        print(*args, file=sys.stderr, **kwargs)
    except (ValueError, OSError):
        kwargs.pop("file", None)
        try:
            print(*args, **kwargs)
        except Exception:
            pass


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
    # No-ask mode: auto-proceed with default when JANUS_NO_ASK_USER=1
    if os.environ.get("JANUS_NO_ASK_USER") == "1":
        auto_answer = default or "auto-proceed"
        _safe_print(f"   [no-ask mode] {question} → {auto_answer}")
        return json.dumps({
            "question": question,
            "answer": auto_answer,
            "options": options,
            "auto": True,
        })

    _safe_print("\n" + "═" * 70)
    _safe_print("🤔 AGENT ASKS:")
    _safe_print(f"   {question}")
    _safe_print("═" * 70)

    if options:
        for i, opt in enumerate(options, 1):
            _safe_print(f"   {i}. {opt}")
        _safe_print("   (or type your own answer)")

    if default:
        _safe_print(f"   [default: {default}]")

    try:
        if timeout_s > 0:
            import select
            _safe_write("   > ")
            ready, _, _ = select.select([sys.stdin], [], [], timeout_s)
            if ready:
                answer = sys.stdin.readline().strip()
            else:
                _safe_print(f"(timeout → default: {default})")
                answer = default or ""
        else:
            _safe_write("   > ")
            answer = sys.stdin.readline().strip()
    except (EOFError, KeyboardInterrupt):
        _safe_print("\n   (interrupted → using default)")
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

    _safe_print(f"   → {resolved}")
    _safe_print("═" * 70 + "\n")

    return json.dumps({
        "question": question,
        "answer": resolved,
        "options": options,
    })