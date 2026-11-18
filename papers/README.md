# Papers

This directory is the literature corpus behind the MalariaSentinel models and
their scoring targets. Each primary paper is identified by an entry in
`manifest.json`, which is the single source of truth for the inventory.

## What is tracked

| Path | Tracked | Content |
|---|---|---|
| `manifest.json` | yes | One entry per paper: identifier, class, theme, slug, bibliographic fields, expected status. |
| `REFERENCES.md` | yes | Index generated from `manifest.json`. |
| `README.md` | yes | This file. |
| `<theme>/<slug>/` | no (gitignored) | Per-paper folder: PDF, extracted text, images, `provenance.yaml`. |

Paper text is not versioned. The PDFs and extracted text are gitignored and are
rebuilt locally from the manifest. Do not commit them.

Claims that the code or the scoring targets rely on, with their primary sources,
are recorded in the claims ledger: `docs/papers-traceability.md`.

## Rebuilding the local corpus

From the repository root:

```bash
cd mal-core && uv run malariasim papers fetch && uv run malariasim papers extract && uv run malariasim papers generate
```

`fetch` downloads each entry's PDF (checksum verified) or records why it could
not be obtained. `extract` converts the retrieved PDFs to Markdown and images,
and records the outcome in each paper's `provenance.yaml`. `generate` renders
`REFERENCES.md` from the manifest.

## Status vocabulary

Each entry has an `expected_status` (hand-authored in the manifest) and an
`observed_status` (written by the tool to `provenance.yaml`). Both use the same
values:

| Status | Meaning |
|---|---|
| `ok` | The paper was retrieved and extracted. |
| `pending_no_source` | No resolvable source (no DOI, or none found). |
| `pending_paywalled` | A source exists but the full text is not accessible without a subscription. |
| `pending_network` | The fetch failed for a transient reason; retry later. |
| `pending_extraction_failed` | The PDF was retrieved but text extraction failed. |
| `withdrawn` | The paper has been retracted or withdrawn by the publisher. |

## Licences

The `licence_as_recorded` field is informational. It does not gate any
operation on the corpus.
