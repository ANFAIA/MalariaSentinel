"""
Audio Mixer — Post-processes raw podcast audio with ffmpeg.

Handles: normalization, background music ducking, concat, MP3 export.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    return shutil.which("ffmpeg") is not None


def normalize_audio(input_path: str, output_path: str, target_loudness: float = -16.0) -> str:
    """Normalize audio loudness using ffmpeg loudnorm filter."""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", f"loudnorm=I={target_loudness}:TP=-1.5:LRA=11",
        "-ar", "44100",
        "-ac", "2",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Normalized: {output_path}")
    return output_path


def add_background_music(
    audio_path: str,
    music_path: str,
    output_path: str,
    music_volume: float = 0.15,
    fade_in: float = 3.0,
    fade_out: float = 5.0,
) -> str:
    """Mix background music under speech with auto-ducking."""
    probe = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip())

    music_filter = (
        f"aloop=loop=-1:size=2e+09,"
        f"atrim=0:{duration + fade_out},"
        f"afade=t=in:d={fade_in},"
        f"afade=t=out:st={duration - fade_out}:d={fade_out},"
        f"volume={music_volume}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", audio_path,
        "-i", music_path,
        "-filter_complex",
        f"[1:a]{music_filter}[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[out]",
        "-map", "[out]",
        "-ar", "44100",
        "-ac", "2",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Music mixed: {output_path}")
    return output_path


def export_mp3(input_path: str, output_path: str, bitrate: str = "192k") -> str:
    """Export audio to MP3 format."""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-codec:a", "libmp3lame",
        "-b:a", bitrate,
        "-ar", "44100",
        "-ac", "2",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"MP3 exported: {output_path}")
    return output_path


def copy_subtitles(srt_path: str, output_path: str) -> Optional[str]:
    """Copy SRT subtitle file to output location."""
    if not Path(srt_path).exists():
        return None
    shutil.copy2(srt_path, output_path)
    print(f"Subtitles copied: {output_path}")
    return output_path


def process_audio(
    raw_wav: str,
    output_dir: str,
    srt_path: Optional[str] = None,
    music_path: Optional[str] = None,
    music_volume: float = 0.15,
    normalize: bool = True,
    title: str = "podcast",
) -> dict:
    """Full post-processing pipeline."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    safe_title = "".join(c if c.isalnum() or c in "-_" else "-" for c in title)
    safe_title = safe_title[:60]

    current = raw_wav
    outputs = {}

    if normalize:
        norm_path = str(out / f"{safe_title}_normalized.wav")
        current = normalize_audio(current, norm_path)
        outputs["normalized_wav"] = current

    if music_path and Path(music_path).exists():
        mixed_path = str(out / f"{safe_title}_mixed.wav")
        current = add_background_music(current, music_path, mixed_path, music_volume)
        outputs["mixed_wav"] = current

    mp3_path = str(out / f"{safe_title}.mp3")
    export_mp3(current, mp3_path)
    outputs["mp3"] = mp3_path

    if srt_path:
        srt_out = str(out / f"{safe_title}.srt")
        result = copy_subtitles(srt_path, srt_out)
        if result:
            outputs["srt"] = result

    return outputs
