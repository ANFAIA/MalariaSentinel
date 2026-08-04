"""
Audio Generator — Wraps podcast_tts to generate WAV segments from a podcast script.

Uses Kokoro-82M as the local TTS engine.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# Add parent scripts dir to path for voice imports
sys.path.insert(0, str(Path(__file__).parent))
from voices import get_lang_code, get_voices_for_language, parse_voice_string


async def generate_solo_audio(
    script: dict,
    output_dir: str,
    voice_overrides: Optional[str] = None,
    speed: float = 1.0,
) -> str:
    """Generate audio for a solo podcast script.

    Args:
        script: Podcast script dict with segments.
        output_dir: Directory to write output files.
        voice_overrides: Comma-separated voice IDs to override defaults.
        speed: Speech speed multiplier.

    Returns:
        Path to the generated WAV file.
    """
    from podcast_tts import PodcastTTS

    language = script.get("language", "en")
    lang_code = get_lang_code(language)

    # Resolve voice
    if voice_overrides:
        voice_map = parse_voice_string(voice_overrides, language)
        voice_id = voice_map.get("host")
    else:
        defaults = get_voices_for_language(language)
        voice_id = defaults["host_a"].voice_id

    tts = PodcastTTS(engine="kokoro", language=language)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Concatenate all segment texts
    full_text = "\n\n".join(seg["text"] for seg in script["segments"])

    output_file = str(out_path / "podcast_raw.wav")

    await tts.generate_tts(
        text=full_text,
        speaker=voice_id,
        filename=output_file,
        channel="both",
    )

    print(f"Solo audio saved: {output_file}")
    return output_file


async def generate_dialog_audio(
    script: dict,
    output_dir: str,
    voice_overrides: Optional[str] = None,
    pause_duration: float = 0.5,
) -> str:
    """Generate audio for a dialog podcast script.

    Args:
        script: Podcast script dict with segments.
        output_dir: Directory to write output files.
        voice_overrides: Comma-separated voice IDs (e.g. "am_adam,af_bella").
        pause_duration: Pause between speakers in seconds.

    Returns:
        Path to the generated WAV file.
    """
    from podcast_tts import PodcastTTS

    language = script.get("language", "en")
    defaults = get_voices_for_language(language)

    # Parse voice overrides
    if voice_overrides:
        voice_map = parse_voice_string(voice_overrides, language)
    else:
        voice_map = {role: preset.voice_id for role, preset in defaults.items()}

    tts = PodcastTTS(engine="kokoro", language=language)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Build texts list: [{"voice_id": ["text", "channel"]}, ...]
    # podcast_tts expects DialogEntry = dict[str, list]
    texts = []
    for i, seg in enumerate(script["segments"]):
        speaker = seg["speaker"]
        voice_id = voice_map.get(speaker)
        if not voice_id:
            voice_id = list(voice_map.values())[0]
            print(f"Warning: speaker '{speaker}' not in voice map, using {voice_id}")

        channel = "left" if i % 2 == 0 else "right"
        texts.append({voice_id: [seg["text"], channel]})

    output_file = str(out_path / "podcast_raw.wav")

    await tts.generate_dialog(
        texts=texts,
        filename=output_file,
        pause_duration=pause_duration,
        normalize=True,
        subtitles=True,
        subtitle_format="srt",
    )

    print(f"Dialog audio saved: {output_file}")
    return output_file


async def generate_audio(
    script: dict,
    output_dir: str,
    voice_overrides: Optional[str] = None,
    pause_duration: float = 0.5,
    speed: float = 1.0,
) -> tuple[str, Optional[str]]:
    """Generate audio from a podcast script.

    Routes to solo or dialog generation based on script format.

    Returns:
        Tuple of (wav_path, srt_path or None).
    """
    fmt = script.get("format", "solo")
    out_path = Path(output_dir)

    if fmt == "dialog":
        wav = await generate_dialog_audio(
            script, output_dir, voice_overrides, pause_duration
        )
    else:
        wav = await generate_solo_audio(
            script, output_dir, voice_overrides, speed
        )

    # Check for SRT subtitle file
    srt_path = out_path / "podcast_raw.srt"
    srt = str(srt_path) if srt_path.exists() else None

    return wav, srt


def generate_audio_sync(
    script: dict,
    output_dir: str,
    voice_overrides: Optional[str] = None,
    pause_duration: float = 0.5,
    speed: float = 1.0,
) -> tuple[str, Optional[str]]:
    """Synchronous wrapper for generate_audio."""
    return asyncio.run(
        generate_audio(script, output_dir, voice_overrides, pause_duration, speed)
    )
