---
name: podcast-gen
description: "Generate podcasts from text using LLM + local TTS. Converts articles, posts, notes into natural-sounding podcast audio (solo or dialog format). Uses OpenRouter LLM (xiaomi/mimo-v2.5) to rewrite text as conversational scripts, then Kokoro-82M for local audio generation. Supports Spanish (Spain) and English. Triggers on: podcast, generate podcast, text-to-podcast, convert to audio, audio version, narrate this, read aloud."
version: "1.0.0"
category: media
tags: [tts, podcast, audio, openrouter, kokoro, local]
---

# Podcast Generator

Convert any text into a natural-sounding podcast — solo narrator or multi-host dialog — using a local TTS engine and an LLM script rewriter.

## Architecture

```
Input text ──→ LLM (OpenRouter xiaomi/mimo-v2.5) ──→ Structured podcast script JSON
                                                              │
                                                              ▼
                                                    Kokoro-82M (local TTS)
                                                              │
                                                              ▼
                                                    WAV segments ──→ ffmpeg ──→ MP3 + SRT
```

## Prerequisites

Install before first use:

```bash
# System deps (macOS)
brew install espeak-ng ffmpeg

# Python deps
pip install "podcast_tts[kokoro]" openai
```

Models are auto-downloaded to ~/.cache/huggingface/ on first use (~350MB for Kokoro-82M).

## Quick Start

```bash
# Solo podcast from text
python agents/skills/podcast-gen/scripts/generate_podcast.py \
  --text "La IA está transformando la medicina en África..." \
  --format solo \
  --language es \
  --output ./my_podcast/

# Dialog podcast from file
python agents/skills/podcast-gen/scripts/generate_podcast.py \
  --input article.md \
  --format dialog \
  --language en

# From URL
python agents/skills/podcast-gen/scripts/generate_podcast.py \
  --url "https://example.com/blog-post" \
  --format dialog \
  --language es

# Dry run (script only, no audio)
python agents/skills/podcast-gen/scripts/generate_podcast.py \
  --text "Topic here" \
  --format solo \
  --dry-run
```

## CLI Reference

| Flag | Description | Default |
|---|---|---|
| --text "..." | Inline text input | — |
| --input FILE | Read text from file | — |
| --url URL | Extract content from URL | — |
| --script FILE | Pre-generated script JSON (skip LLM) | — |
| --format solo\|dialog | Podcast format | solo |
| --language es\|en\|en-gb | Output language | en |
| --model MODEL | OpenRouter model | xiaomi/mimo-v2.5 |
| --voices "v1,v2" | Override voice IDs | auto |
| --output DIR | Output directory | ./podcast_output |
| --music FILE | Background music | — |
| --music-volume FLOAT | Music volume (0-1) | 0.15 |
| --no-normalize | Skip loudness normalization | false |
| --pause SECS | Pause between speakers | 0.5 |
| --save-script FILE | Save script JSON | — |
| --dry-run | Generate script only | — |
| --list-voices | List available voices | — |

## Voice Presets

### Spanish (Spain)

| Role | Voice ID | Gender |
|---|---|---|
| host_a | ef_dora | Woman |
| host_b | em_alex | Man |

### English (US)

| Role | Voice ID | Gender |
|---|---|---|
| host_a | af_heart | Woman |
| host_b | am_adam | Man |

Override: --voices "am_michael,af_bella"

## Agent Usage

When the user asks to generate a podcast from text:

1. Check if podcast_tts is installed: pip show podcast-tts
2. If not installed, run: pip install "podcast_tts[kokoro]" openai + brew install espeak-ng
3. Run the CLI with appropriate flags
4. Report output file paths and sizes

## Output Files

| File | Description |
|---|---|
| *.mp3 | Final podcast audio (192kbps) |
| *.srt | Subtitle file (if dialog mode) |
| *_normalized.wav | Normalized intermediate WAV |
| script.json | Generated script (with --save-script) |

## Limitations

- Kokoro-82M is good but not ElevenLabs-tier quality. Voice cloning not supported.
- First run downloads ~350MB model weights to ~/.cache/huggingface/.
- English voices are richer (54 options) than Spanish (2 options).
- Background music requires an existing music file (no music generation).
- Python 3.11-3.12 required (Kokoro constraint).
