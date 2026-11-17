#!/usr/bin/env python3
"""check_agentic_models.py — the workflow's provider must match the file.

The workflow that runs the agentic review writes the provider's definition
into the agent's directory **itself**, from a heredoc, because a pull
request must not be able to redirect the endpoint the credential is sent
to. That heredoc and `.github/agentic-reviewers/models.json` — the file a
local run uses — are therefore two copies of the same thing, and two
copies drift.

This tool is the drift guard: it reads the workflow, extracts the heredoc,
and fails when the two are not the same document. It is a check, not a
judgement: the workflow's copy is the one that runs, and this says so when
the other one is stale.

    uv run python tools/check_agentic_models.py

Exit status: 0 when the two agree, 1 when they do not.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

WORKFLOW = REPO / ".github" / "workflows" / "agentic-doc-review.yml"
MODELS_FILE = REPO / ".github" / "agentic-reviewers" / "models.json"

#: The heredoc that carries the provider's definition in the workflow.
HEREDOC = re.compile(
    r"<<'MODELS'\n(?P<body>.*?)\n\s*MODELS\n", re.DOTALL
)


def inline_provider(text: str) -> dict:
    """The provider's definition as the workflow writes it."""
    match = HEREDOC.search(text)
    if match is None:
        raise ValueError("the workflow has no MODELS heredoc")
    body = match.group("body")
    lines = body.split("\n")
    indent = min(len(line) - len(line.lstrip()) for line in lines if line.strip())
    return json.loads("\n".join(line[indent:] for line in lines))


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    try:
        inline = inline_provider(text)
    except (ValueError, json.JSONDecodeError) as error:
        print(f"check_agentic_models: {error}")
        return 1

    on_file = json.loads(MODELS_FILE.read_text(encoding="utf-8"))

    if inline == on_file:
        print("check_agentic_models: the workflow and the file agree")
        return 0

    print("check_agentic_models: the workflow's provider and")
    print(f"  {MODELS_FILE.relative_to(REPO)} disagree.")
    inline_models = {
        model["id"]
        for provider in inline.get("providers", {}).values()
        for model in provider.get("models", [])
    }
    file_models = {
        model["id"]
        for provider in on_file.get("providers", {}).values()
        for model in provider.get("models", [])
    }
    if inline_models != file_models:
        print(f"  the workflow declares: {sorted(inline_models)}")
        print(f"  the file declares:     {sorted(file_models)}")
    for name, provider in inline.get("providers", {}).items():
        other = on_file.get("providers", {}).get(name)
        if other is None:
            print(f"  the workflow declares a provider the file does not: {name}")
            continue
        for model in provider.get("models", []):
            twin = next(
                (m for m in other.get("models", []) if m.get("id") == model.get("id")),
                None,
            )
            if twin is None:
                continue
            for field in ("baseUrl", "api", "contextWindow", "maxTokens"):
                if model.get(field) != twin.get(field):
                    print(
                        f"  {name}/{model.get('id')}: the workflow says "
                        f"{field}={model.get(field)!r}, the file says "
                        f"{twin.get(field)!r}"
                    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
