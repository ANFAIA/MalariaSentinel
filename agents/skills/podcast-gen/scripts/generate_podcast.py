#!/usr/bin/env python3
"""
Podcast Generator — CLI entry point.

End-to-end pipeline: input text → LLM script → local TTS → mixed MP3.

Usage:
    python generate_podcast.py --text "Your article text here" --format solo --language es
    python generate_podcast.py --input article.md --format dialog --language en
    python generate_podcast.py --url "https://example.com/post" --output ./my_podcast/
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Resolve scripts dir for imports
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from llm_script_gen import (
    generate_script,
    generate_script_from_file,
    generate_script_from_url,
)
from audio_gen import generate_audio_sync
from mixer import process_audio, check_ffmpeg
from voices import list_voices


def main():
    parser = argparse.ArgumentParser(
        description="Generate a podcast from text using LLM + local TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --text "AI is changing everything..." --format solo --language en
  %(prog)s --input blog_post.md --format dialog --language es
  %(prog)s --url "https://example.com/article" --output ./my_podcast/
  %(prog)s --list-voices --language es
        """,
    )

    # Input sources (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--text", help="Inline text to convert")
    input_group.add_argument("--input", dest="input_file", help="Path to text file")
    input_group.add_argument("--url", help="URL to extract content from")
    input_group.add_argument(
        "--script", dest="script_file",
        help="Pre-generated script JSON (skip LLM step)",
    )

    # Podcast options
    parser.add_argument(
        "--format",
        choices=["solo", "dialog"],
        default="solo",
        help="Podcast format: solo (1 host) or dialog (2 hosts). Default: solo",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language code: es, en, en-gb. Default: en",
    )
    parser.add_argument(
        "--model",
        default="xiaomi/mimo-v2.5",
        help="OpenRouter model for script generation. Default: xiaomi/mimo-v2.5",
    )
    parser.add_argument(
        "--voices",
        help="Voice override IDs, comma-separated (e.g. 'am_adam,af_bella')",
    )
    parser.add_argument(
        "--output", "-o",
        default="./podcast_output",
        help="Output directory. Default: ./podcast_output",
    )
    parser.add_argument(
        "--music",
        help="Path to background music file (optional)",
    )
    parser.add_argument(
        "--music-volume",
        type=float,
        default=0.15,
        help="Background music volume (0.0-1.0). Default: 0.15",
    )
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help="Skip audio normalization",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.5,
        help="Pause between speakers in dialog mode (seconds). Default: 0.5",
    )

    # Utility
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available voices and exit",
    )
    parser.add_argument(
        "--save-script",
        help="Save generated script JSON to this path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate script only, skip audio generation",
    )

    args = parser.parse_args()

    # ── List voices mode ──────────────────────────────────────────────────
    if args.list_voices:
        list_voices(args.language)
        return

    # ── Validate inputs ───────────────────────────────────────────────────
    if not any([args.text, args.input_file, args.url, args.script_file]):
        parser.error("Provide one of: --text, --input, --url, or --script")

    if not check_ffmpeg():
        print("Error: ffmpeg not found. Install with: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    # ── Step 1: Generate or load script ───────────────────────────────────
    print("=" * 60)
    print("PODCAST GENERATOR")
    print("=" * 60)

    if args.script_file:
        print(f"\n[1/3] Loading script from: {args.script_file}")
        with open(args.script_file, "r", encoding="utf-8") as f:
            script = json.load(f)
    else:
        print(f"\n[1/3] Generating script via LLM ({args.model})...")
        if args.text:
            script = generate_script(
                args.text, args.format, args.model, language=args.language
            )
        elif args.input_file:
            script = generate_script_from_file(
                args.input_file, args.format, args.model, language=args.language
            )
        else:
            script = generate_script_from_url(
                args.url, args.format, args.model, language=args.language
            )

    print(f"   Title: {script['title']}")
    print(f"   Format: {script['format']}")
    print(f"   Language: {script['language']}")
    print(f"   Segments: {len(script['segments'])}")

    # Save script if requested
    if args.save_script:
        save_path = Path(args.save_script)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(
            json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"   Script saved to: {args.save_script}")

    if args.dry_run:
        print("\n[Dry run] Script generated. Skipping audio.")
        print(json.dumps(script, indent=2, ensure_ascii=False))
        return

    # ── Step 2: Generate audio ────────────────────────────────────────────
    print(f"\n[2/3] Generating audio via Kokoro-82M (local)...")

    with tempfile.TemporaryDirectory(prefix="podcast_gen_") as tmpdir:
        wav_path, srt_path = generate_audio_sync(
            script=script,
            output_dir=tmpdir,
            voice_overrides=args.voices,
            pause_duration=args.pause,
        )

        # ── Step 3: Post-process ──────────────────────────────────────────
        print(f"\n[3/3] Post-processing (normalize, export MP3)...")
        outputs = process_audio(
            raw_wav=wav_path,
            output_dir=args.output,
            srt_path=srt_path,
            music_path=args.music,
            music_volume=args.music_volume,
            normalize=not args.no_normalize,
            title=script["title"],
        )

    # ── Done ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("DONE! Output files:")
    print("=" * 60)
    for key, path in sorted(outputs.items()):
        size = os.path.getsize(path)
        print(f"  {key}: {path} ({size / 1024:.1f} KB)")
    print()


if __name__ == "__main__":
    main()
