"""
LLM Script Generator — Converts input text into a structured podcast script via OpenRouter.

Uses xiaomi/mimo-v2.5 by default. Outputs a JSON podcast script with segments,
speaker assignments, and voice mappings.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from openai import OpenAI

DEFAULT_MODEL = "xiaomi/mimo-v2.5"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

SOLO_PROMPT = """You are a podcast scriptwriter. Transform the following text into a natural podcast script for a SOLO host.

RULES:
- Write in the SAME language as the input text.
- Convert written/formal language into conversational spoken language.
- Add natural transitions, emphasis markers, and pacing cues.
- Include an intro greeting and an outro with a call to action.
- Split into logical segments (2-6 paragraphs each).
- Do NOT just read the text verbatim — rewrite it as if explaining to a friend.
- Use short sentences, rhetorical questions, and natural pauses.

OUTPUT FORMAT (strict JSON, no markdown fences):
{
  "title": "string — episode title",
  "format": "solo",
  "language": "es or en (match input language)",
  "segments": [
    {
      "speaker": "host",
      "text": "string — the spoken text for this segment",
      "pause_after_ms": 500
    }
  ]
}"""

DIALOG_PROMPT = """You are a podcast scriptwriter. Transform the following text into a natural DIALOG podcast script between two hosts.

RULES:
- Write in the SAME language as the input text.
- Host A introduces topics, Host B provides analysis/reactions.
- Make it feel like a REAL conversation — interruptions, reactions, follow-ups.
- Add natural speech markers: "hmm", "right", "exactly", "that's interesting".
- Include banter, questions, and back-and-forth dynamics.
- Split into logical segments (2-6 exchanges each).
- Do NOT just read the text verbatim — rewrite it as a lively discussion.

OUTPUT FORMAT (strict JSON, no markdown fences):
{
  "title": "string — episode title",
  "format": "dialog",
  "language": "es or en (match input language)",
  "segments": [
    {
      "speaker": "host_a",
      "text": "string — spoken text",
      "pause_after_ms": 300
    },
    {
      "speaker": "host_b",
      "text": "string — response text",
      "pause_after_ms": 400
    }
  ]
}"""


def generate_script(
    text: str,
    format: str = "solo",
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    language: Optional[str] = None,
) -> dict:
    """Generate a podcast script from input text using OpenRouter LLM.

    Args:
        text: Input text to transform into a podcast script.
        format: "solo" for monologue, "dialog" for two-host conversation.
        model: OpenRouter model identifier.
        api_key: OpenRouter API key. Falls back to OPENROUTER_API_KEY env var.
        language: Force language ("es" or "en"). If None, auto-detect from text.

    Returns:
        Parsed podcast script dict with title, format, language, segments.
    """
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "No API key. Set OPENROUTER_API_KEY env var or pass api_key."
        )

    client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=api_key,
    )

    system_prompt = SOLO_PROMPT if format == "solo" else DIALOG_PROMPT

    if language:
        system_prompt += f"\n\nIMPORTANT: Output language must be '{language}'."

    user_content = f"Transform this text into a podcast script:\n\n---\n{text}\n---"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
        max_tokens=4096,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Remove first and last lines (fences)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)

    try:
        script = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\n\nRaw output:\n{raw}")

    # Validate structure
    required_keys = {"title", "format", "language", "segments"}
    missing = required_keys - set(script.keys())
    if missing:
        raise ValueError(f"Script missing keys: {missing}")

    if not script["segments"]:
        raise ValueError("Script has no segments")

    return script


def generate_script_from_file(
    file_path: str,
    format: str = "solo",
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    language: Optional[str] = None,
) -> dict:
    """Read a text file and generate a podcast script."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = path.read_text(encoding="utf-8")
    return generate_script(
        text=text,
        format=format,
        model=model,
        api_key=api_key,
        language=language,
    )


def generate_script_from_url(
    url: str,
    format: str = "solo",
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    language: Optional[str] = None,
) -> dict:
    """Fetch a URL content and generate a podcast script.

    Uses the LLM itself to extract and summarize the URL content.
    """
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("No API key. Set OPENROUTER_API_KEY env var.")

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)

    # First: extract content from URL via LLM
    extract_response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Extract the full main content from this URL. Return ONLY the text content, no commentary.",
            },
            {"role": "user", "content": f"Extract content from: {url}"},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    extracted_text = extract_response.choices[0].message.content.strip()
    return generate_script(
        text=extracted_text,
        format=format,
        model=model,
        api_key=api_key,
        language=language,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate podcast script via LLM")
    parser.add_argument("--text", help="Inline text input")
    parser.add_argument("--input", dest="input_file", help="Path to text file")
    parser.add_argument("--url", help="URL to extract content from")
    parser.add_argument(
        "--format",
        choices=["solo", "dialog"],
        default="solo",
        help="Podcast format (default: solo)",
    )
    parser.add_argument("--language", help="Force language (es/en)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenRouter model")
    parser.add_argument("--output", help="Output JSON path (default: stdout)")
    args = parser.parse_args()

    if not any([args.text, args.input_file, args.url]):
        parser.error("Provide --text, --input, or --url")

    if args.text:
        script = generate_script(args.text, args.format, args.model, language=args.language)
    elif args.input_file:
        script = generate_script_from_file(args.input_file, args.format, args.model, language=args.language)
    else:
        script = generate_script_from_url(args.url, args.format, args.model, language=args.language)

    output = json.dumps(script, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Script saved to {args.output}")
    else:
        print(output)
