#!/usr/bin/env python3
"""CLI entrypoint for the Social Networks Agent.

Usage:
    cd social-networks/agent
    python run.py
    python run.py --model openai:gpt-4.1 --thread-id my-session
"""
from __future__ import annotations
import argparse
import os
import sys

def main() -> None:
    # Allow running directly from the agent/ directory
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from main import create_agent
    
    parser = argparse.ArgumentParser(description="Social Networks Agent — interactive CLI")
    parser.add_argument("--model", default="anthropic:claude-sonnet-4-5-20250929")
    parser.add_argument("--thread-id", default="cli-session")
    args = parser.parse_args()
    
    print(f"Creating agent with model: {args.model}")
    agent = create_agent(model=args.model)
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
        sys.exit(0)

if __name__ == "__main__":
    main()
