---
name: audio-to-content
description: Transcribe audio files with Parakeet v3 (local, no API) and generate social media content from the transcription. Use when the user says "transcribe this audio", "pass audio to text", "convert this recording", "generate content from audio", or wants to create LinkedIn/social posts from a voice recording. Searches for audio in common locations, handles format conversion, transcribes with sherpa-onnx, and produces both a raw transcription and a platform-ready description.
---

# Audio to Social Content

Transcribe audio locally using NVIDIA Parakeet v3 via sherpa-onnx, then generate social media content from the result. No cloud APIs, no Docker, no external services.

## When to use

- User has an audio/video file and wants the text content
- User wants to create a LinkedIn post, video description, or social content from a recording
- User says "transcribe", "audio to text", "pass this to text", "what's in this audio"

## Prerequisites

- **ffmpeg** — for audio format conversion (pre-installed on macOS)
- **sherpa-onnx** — Python package for local inference
- **Parakeet v3 model** — already downloaded at `~/.config/openchamber/speech-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/`

## Workflow

### 1. Find the audio file

Search in common locations. Ask the user if not found.

```bash
# Search common locations
find /Volumes/ -maxdepth 4 -type f \( -name "*.wav" -o -name "*.mp3" -o -name "*.m4a" -o -name "*.ogg" -o -name "*.flac" \) 2>/dev/null
find ~/Downloads -maxdepth 3 -type f \( -name "*.wav" -o -name "*.mp3" \) 2>/dev/null
find ~/Desktop -maxdepth 3 -type f \( -name "*.wav" -o -name "*.mp3" \) 2>/dev/null
```

If the user gives a filename, search by name:

```bash
find /Volumes/ -maxdepth 5 -type f -name "FILENAME" 2>/dev/null
```

### 2. Install sherpa-onnx (if needed)

```bash
pip3 install sherpa-onnx
```

Check if already installed:

```bash
python3 -c "import sherpa_onnx" 2>&1
```

### 3. Convert audio to compatible format

Parakeet v3 expects 16kHz or 24kHz mono 16-bit WAV. Use ffmpeg to convert:

```bash
ffmpeg -i INPUT -ar 24000 -ac 1 -sample_fmt s16 /tmp/audio_converted.wav -y
```

**Why 24kHz**: the Parakeet test files are 24kHz and work without issues. 48kHz stereo causes ONNX broadcast errors.

**Why this matters**: the model has a strict shape contract. Wrong sample rate or channel count causes a runtime error like:

```
BroadcastIterator::Init axis == 1 || axis == largest was false. Attempting to broadcast an axis by a dimension other than 1.
```

### 4. Transcribe with sherpa-onnx

Use this exact Python script. Key details:

- `model_type="nemo"` — required for NeMo Parakeet models (even though it shows a warning, it works)
- `feature_dim=128` — Parakeet uses 128-dim features, not the default 80
- Process in **30-second chunks** — long audio (>60s) causes ONNX shape errors if fed in one pass
- The model internally resamples to 16kHz

```python
import sherpa_onnx
import os
import wave
import numpy as np

model_dir = os.path.expanduser("~/.config/openchamber/speech-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8")

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

audio_file = "/tmp/audio_converted.wav"

with wave.open(audio_file, "rb") as wf:
    sr = wf.getframerate()
    n_channels = wf.getnchannels()
    sampwidth = wf.getsampwidth()
    n_frames = wf.getnframes()
    raw = wf.readframes(n_frames)

samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

# Process in 30-second chunks
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

full_text = "\n".join(all_text)
print(full_text)
```

### 5. Save transcription

Save to the same directory as the original audio:

```
same_directory/AUDIO_transcripcion.txt
```

### 6. Generate social media content

Based on the transcription, generate a markdown file with:

- **Video title** — short, direct
- **What the video covers** — 3-5 bullet points
- **What it does NOT cover** — honest about scope
- **Target platform** — LinkedIn, Twitter, etc.
- **Suggested hashtags**

Follow the tone rules from `linkedin-post.md`:

- Conversational, first-person
- No hype, no "thrilled to announce"
- Honest about limitations
- Under 150 words for the post body

Save as:

```
same_directory/descripcion_video.md
```

### 7. Clean up

Remove the temporary converted file:

```bash
rm /tmp/audio_converted.wav
```

## Pitfalls

### 1. 24-bit audio (3 bytes per sample)
**Problem**: `wave.readframes()` returns raw bytes. 24-bit WAV has 3 bytes per sample, which numpy doesn't handle natively.
**Fix**: Use ffmpeg to convert to 16-bit: `-sample_fmt s16`. Never try to parse 24-bit manually.

### 2. model_type must be "nemo"
**Problem**: Parakeet TDT models fail with the default `model_type="transducer"` because the decoder metadata lacks `vocab_size`.
**Fix**: Always pass `model_type="nemo"`. The warning "Invalid model_type: nemo" is expected and harmless.

### 3. Long audio causes ONNX broadcast error
**Problem**: Audio longer than ~60 seconds fed in one pass causes a shape mismatch in the self-attention layer.
**Fix**: Always chunk into 30-second segments. Re-create the stream for each chunk.

### 4. feature_dim must be 128
**Problem**: Default `feature_dim=80` is for Whisper-style models. Parakeet uses 128-dim features.
**Fix**: Always pass `feature_dim=128` explicitly.

### 5. 48kHz stereo causes errors
**Problem**: Even though sherpa-onnx has a resampler, 48kHz stereo input triggers ONNX broadcast errors.
**Fix**: Always convert to 24kHz mono before feeding to the model.

## Model location

The Parakeet v3 model is stored at:

```
~/.config/openchamber/speech-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8/
```

Files:
- `encoder.int8.onnx` (~620MB)
- `decoder.int8.onnx` (~11MB)
- `joiner.int8.onnx` (~6MB)
- `tokens.txt` (~94KB)

If the model is not present, it can be downloaded from HuggingFace: `nvidia/parakeet-tdt-0.6b-v3` (the sherpa-onnx converted version).

## Integration with other skills

This skill produces raw material for:

- **LinkedIn Presentation Builder** (`social-networks/SKILL.md`) — use the transcription as source content for carousels/videos
- **LinkedIn Post Generator** (`social-networks/linkedin-post.md`) — feed the transcription into the post template
- Any social platform content pipeline
