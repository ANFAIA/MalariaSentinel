"""
Voice presets for Kokoro-82M TTS.

Maps language + speaker roles to Kokoro voice IDs.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class VoicePreset:
    voice_id: str
    label: str
    gender: str  # "f" or "m"
    language: str  # kokoro lang_code: "a", "b", "e", etc.


# ── Spanish (Spain) — lang_code "e" ──────────────────────────────────────────

SPANISH_VOICES = {
    "host_a": VoicePreset(
        voice_id="ef_dora",
        label="Dora — Mujer España",
        gender="f",
        language="e",
    ),
    "host_b": VoicePreset(
        voice_id="em_alex",
        label="Alex — Hombre España",
        gender="m",
        language="e",
    ),
}

# ── English (US) — lang_code "a" ─────────────────────────────────────────────

ENGLISH_US_VOICES = {
    "host_a": VoicePreset(
        voice_id="af_heart",
        label="Heart — Woman US",
        gender="f",
        language="a",
    ),
    "host_b": VoicePreset(
        voice_id="am_adam",
        label="Adam — Man US",
        gender="m",
        language="a",
    ),
}

# ── English (UK) — lang_code "b" ─────────────────────────────────────────────

ENGLISH_UK_VOICES = {
    "host_a": VoicePreset(
        voice_id="bf_emma",
        label="Emma — Woman UK",
        gender="f",
        language="b",
    ),
    "host_b": VoicePreset(
        voice_id="bm_george",
        label="George — Man UK",
        gender="m",
        language="b",
    ),
}

# ── Registry ──────────────────────────────────────────────────────────────────

LANGUAGE_PRESETS = {
    "es": SPANISH_VOICES,
    "en": ENGLISH_US_VOICES,
    "en-gb": ENGLISH_UK_VOICES,
}

# All available Kokoro voices for reference
ALL_KOKORO_VOICES = {
    # Spanish
    "ef_dora": "Dora (es, f)",
    "em_alex": "Alex (es, m)",
    # English US
    "af_alloy": "Alloy (en-us, f)",
    "af_aoede": "Aoede (en-us, f)",
    "af_bella": "Bella (en-us, f)",
    "af_heart": "Heart (en-us, f)",
    "af_jessica": "Jessica (en-us, f)",
    "af_kore": "Kore (en-us, f)",
    "af_nicole": "Nicole (en-us, f)",
    "af_nova": "Nova (en-us, f)",
    "af_river": "River (en-us, f)",
    "af_sarah": "Sarah (en-us, f)",
    "af_sky": "Sky (en-us, f)",
    "am_adam": "Adam (en-us, m)",
    "am_echo": "Echo (en-us, m)",
    "am_eric": "Eric (en-us, m)",
    "am_fenrir": "Fenrir (en-us, m)",
    "am_liam": "Liam (en-us, m)",
    "am_michael": "Michael (en-us, m)",
    "am_onyx": "Onyx (en-us, m)",
    "am_puck": "Puck (en-us, m)",
    # English UK
    "bf_alice": "Alice (en-gb, f)",
    "bf_emma": "Emma (en-gb, f)",
    "bf_isabella": "Isabella (en-gb, f)",
    "bf_lily": "Lily (en-gb, f)",
    "bm_daniel": "Daniel (en-gb, m)",
    "bm_fable": "Fable (en-gb, m)",
    "bm_george": "George (en-gb, m)",
    "bm_lewis": "Lewis (en-gb, m)",
    # French
    "ff_siwis": "Siwis (fr, f)",
    # Italian
    "if_sara": "Sara (it, f)",
    "im_nicola": "Nicola (it, m)",
    # Japanese
    "jf_alpha": "Alpha (ja, f)",
    "jm_kumo": "Kumo (ja, m)",
    # Chinese
    "zf_xiaobei": "Xiaobei (zh, f)",
    "zm_yunxi": "Yunxi (zh, m)",
}


def get_voices_for_language(language: str) -> dict[str, VoicePreset]:
    """Get default voice presets for a language code.

    Args:
        language: ISO language code ("es", "en", "en-gb").

    Returns:
        Dict mapping speaker roles to VoicePreset.
    """
    if language not in LANGUAGE_PRESETS:
        available = ", ".join(LANGUAGE_PRESETS.keys())
        raise ValueError(
            f"Language '{language}' not supported. Available: {available}"
        )
    return LANGUAGE_PRESETS[language]


def get_lang_code(language: str) -> str:
    """Get Kokoro lang_code for a language.

    Args:
        language: ISO language code ("es", "en", "en-gb").

    Returns:
        Kokoro single-letter lang_code.
    """
    voices = get_voices_for_language(language)
    # All voices in a preset share the same lang_code
    return list(voices.values())[0].language


def parse_voice_string(voice_str: str, language: str) -> dict[str, str]:
    """Parse a voice override string like 'am_adam,af_bella'.

    Args:
        voice_str: Comma-separated voice IDs (e.g. "am_adam,af_bella").
        language: Fallback language for auto-assignment.

    Returns:
        Dict mapping speaker roles to voice IDs.
    """
    voices = [v.strip() for v in voice_str.split(",")]
    defaults = get_voices_for_language(language)

    result = {}
    roles = list(defaults.keys())

    for i, voice_id in enumerate(voices):
        role = roles[i] if i < len(roles) else f"host_{i}"
        # Validate voice exists
        if voice_id not in ALL_KOKORO_VOICES:
            print(
                f"Warning: voice '{voice_id}' not in known voices. "
                f"Available: {', '.join(sorted(ALL_KOKORO_VOICES.keys()))}"
            )
        result[role] = voice_id

    return result


def list_voices(language: Optional[str] = None) -> None:
    """Print available voices."""
    if language:
        presets = get_voices_for_language(language)
        print(f"\nVoices for '{language}':")
        for role, preset in presets.items():
            print(f"  {role}: {preset.voice_id} — {preset.label}")
    else:
        print("\nAll Kokoro voices:")
        for vid, label in sorted(ALL_KOKORO_VOICES.items()):
            print(f"  {vid}: {label}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Voice presets for podcast-gen")
    parser.add_argument("--language", help="Show voices for a language")
    parser.add_argument("--list", action="store_true", help="List all voices")
    args = parser.parse_args()

    if args.list or args.language:
        list_voices(args.language)
    else:
        parser.print_help()
