# Script Format Reference

## JSON Schema

```json
{
  "title": "string (required) — episode title, used for filename",
  "format": "string (required) — 'solo' or 'dialog'",
  "language": "string (required) — ISO code: 'es', 'en', 'en-gb'",
  "segments": [
    {
      "speaker": "string (required) — role identifier",
      "text": "string (required) — spoken text, natural language",
      "pause_after_ms": "number (optional) — pause after this segment, default 500"
    }
  ]
}
```

## Speaker Roles

### Solo format
- host — the single narrator

### Dialog format
- host_a — primary host, introduces topics
- host_b — co-host, provides reactions and analysis

## Segment Guidelines

- 2-6 segments per episode (sweet spot: 3-4)
- Each segment: 2-5 sentences (50-150 words)
- pause_after_ms: use longer pauses (800-1200ms) between topic shifts, shorter (300-500ms) between related points
- For dialog: alternate speakers, avoid more than 2 consecutive turns from one speaker
