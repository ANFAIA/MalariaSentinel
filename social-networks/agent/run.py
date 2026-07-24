#!/usr/bin/env python3
"""CLI entrypoint for the Social Networks Agent.

Usage:
    cd social-networks/agent
    python run.py
    python run.py --provider anthropic --model claude-sonnet-4-5-20250929
    python run.py --provider openrouter --model xiaomi/mimo-v2.5
    python run.py --provider openai --model gpt-4.1
"""
from __future__ import annotations
import argparse

def main() -> None:
    parser = argparse.ArgumentParser(description="Social Networks Agent — interactive CLI")
    parser.add_argument(
        "--provider",
        default="anthropic",
        help="Model provider: anthropic, openai, openrouter, google_genai, etc. (default: anthropic)",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-5-20250929",
        help="Model name: claude-sonnet-4-5-20250929, gpt-4.1, xiaomi/mimo-v2.5, etc. (default: claude-sonnet-4-5-20250929)",
    )
    parser.add_argument("--thread-id", default="cli-session")
    args = parser.parse_args()

    from agent.main import create_agent

    print(f"Creating agent: {args.provider}/{args.model}")
    agent = create_agent(provider=args.provider, model=args.model)
    print(f"Agent ready. Type your message (Ctrl+C to exit).\n")

    config = {"configurable": {"thread_id": args.thread_id}}

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break
            result = agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
            )
            if result and "messages" in result:
                last_msg = result["messages"][-1]
                content = getattr(last_msg, "content", None)
                if content:
                    print(f"\nAgent: {content}\n")
            else:
                print("\nAgent: (no response)\n")
    except KeyboardInterrupt:
        print("\n\nExiting.")
        import sys
        sys.exit(0)

if __name__ == "__main__":
    main()
