"""Custom tools for the Social Networks Agent."""

from __future__ import annotations

import os
import subprocess
import tempfile

import wave

from langchain_core.tools import tool

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SOCIAL_DIR = os.path.join(REPO_ROOT, "social-networks")


@tool
def transcribe_audio(audio_path: str) -> str:
    """Transcribe an audio file to text using Parakeet v3 via sherpa-onnx (local, no API).

    Converts audio to 24kHz mono WAV via ffmpeg, then transcribes in 30-second chunks.
    Returns the full transcription text.

    Args:
        audio_path: Path to the audio file (wav, mp3, m4a, ogg, flac).
    """
    try:
        import numpy as np
        import sherpa_onnx
    except ImportError:
        return "Error: sherpa-onnx and numpy are required. Install with: pip3 install sherpa-onnx numpy"

    if not os.path.exists(audio_path):
        return f"Error: audio file not found: {audio_path}"

    model_dir = os.path.expanduser(
        "~/.config/openchamber/speech-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"
    )
    if not os.path.isdir(model_dir):
        return f"Error: Parakeet v3 model not found at {model_dir}"

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        ffmpeg_cmd = [
            "ffmpeg", "-i", audio_path,
            "-ar", "24000", "-ac", "1", "-sample_fmt", "s16",
            tmp_path, "-y",
        ]
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return f"Error converting audio with ffmpeg: {result.stderr}"

        recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=os.path.join(model_dir, "encoder.int8.onnx"),
            decoder=os.path.join(model_dir, "decoder.int8.onnx"),
            joiner=os.path.join(model_dir, "joiner.int8.onnx"),
            tokens=os.path.join(model_dir, "tokens.txt"),
            num_threads=4,
            decoding_method="greedy_search",
            sample_rate=16000,
            feature_dim=128,
            model_type="nemo",
        )

        with wave.open(tmp_path, "rb") as wf:
            sr = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

        chunk_sec = 30
        chunk_size = sr * chunk_sec
        total_chunks = (len(samples) + chunk_size - 1) // chunk_size

        all_text = []
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(samples))
            chunk = samples[start:end]
            stream = recognizer.create_stream()
            stream.accept_waveform(sr, chunk.tolist())
            recognizer.decode_stream(stream)
            text = stream.result.text.strip()
            if text:
                all_text.append(text)

        return "\n".join(all_text) if all_text else "(no speech detected)"

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@tool
def render_hyperframes(composition_dir: str) -> str:
    """Render a HyperFrames composition to MP4 video.

    Runs `npx hyperframes check` then `npx hyperframes render` in the given directory.
    Returns the path to the rendered MP4.

    Args:
        composition_dir: Directory containing the HyperFrames index.html, relative to social-networks/.
    """
    abs_dir = os.path.join(SOCIAL_DIR, composition_dir)
    if not os.path.isdir(abs_dir):
        return f"Error: directory not found: {abs_dir}"

    check_result = subprocess.run(
        ["npx", "hyperframes", "check"],
        cwd=abs_dir, capture_output=True, text=True,
    )
    if check_result.returncode != 0:
        return f"HyperFrames check failed:\n{check_result.stdout}\n{check_result.stderr}"

    render_result = subprocess.run(
        ["npx", "hyperframes", "render"],
        cwd=abs_dir, capture_output=True, text=True,
    )
    if render_result.returncode != 0:
        return f"HyperFrames render failed:\n{render_result.stdout}\n{render_result.stderr}"

    renders_dir = os.path.join(abs_dir, "renders")
    if os.path.isdir(renders_dir):
        mp4s = [f for f in os.listdir(renders_dir) if f.endswith(".mp4")]
        if mp4s:
            latest = sorted(mp4s)[-1]
            return os.path.join(renders_dir, latest)

    return f"Render complete. Check {renders_dir}/ for output."


@tool
def check_hyperframes(composition_dir: str) -> str:
    """Lint and validate a HyperFrames composition (layout, motion, contrast).

    Runs `npx hyperframes check` only — does not render.

    Args:
        composition_dir: Directory containing the HyperFrames index.html, relative to social-networks/.
    """
    abs_dir = os.path.join(SOCIAL_DIR, composition_dir)
    if not os.path.isdir(abs_dir):
        return f"Error: directory not found: {abs_dir}"

    result = subprocess.run(
        ["npx", "hyperframes", "check"],
        cwd=abs_dir, capture_output=True, text=True,
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        return f"Check found issues (exit {result.returncode}):\n{output}"
    return f"Check passed.\n{output}"
