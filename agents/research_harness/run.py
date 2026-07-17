"""CLI entrypoint for the MalariaSentinel research harness.

Default model: MIMO V2.5 (opencode-go/mimo-v2-5)
Override via: --model flag, OPENCODE_MODEL env var, or config.DEFAULT_MODEL
"""

import argparse
import logging
import sys

from .orchestrator import run_research_cycle, run_single_phase
from .config import DEFAULT_MODEL


def main():
    """CLI entrypoint. Sessions run with --auto and --title, so they
    self-approve non-denied permissions and show up under the given title
    in the TUI."""
    parser = argparse.ArgumentParser(
        description="MalariaSentinel Research Harness — orchestrates OpenCode for malaria research"
    )
    parser.add_argument(
        "--mode",
        choices=["search", "condense", "review", "hypothesize", "full"],
        default="full",
        help="Research phase to run (default: full cycle)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Research topic (required for search mode)",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help=f"Model to use (default: {DEFAULT_MODEL}). Format: provider/model",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Pass model to orchestrator via env if specified
    if args.model:
        import os
        os.environ["OPENCODE_MODEL"] = args.model

    if args.mode == "full":
        result = run_research_cycle(args.topic)
    else:
        result = run_single_phase(args.mode, args.topic)

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
