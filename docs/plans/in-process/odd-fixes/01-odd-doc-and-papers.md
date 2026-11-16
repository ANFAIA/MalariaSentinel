# Pack 01 — ODD document automation and papers restructure

> Source: ODD 2010 review notes (`.cache/odd-latex/odd-2010-malariasentinel-notes.tex`).
> Status: initial plan — to be detailed later.

## Objective

Keep the ODD description automatically in sync with the code, make the
protocol accessible to readers, and move the `papers/` folder out of the
GitHub repository while keeping a tool that can regenerate it.

## Notes (verbatim)

- **p.1** — "Create a GitHub Action to update this document for each PR using an agent."
- **p.7** — "Explain shortly what are Elements"
- **p.32** — "Remove papers folder from GitHub; keep only agents/tools to create it with all papers, and keep papers mentioned here as bibliography + input for tool. For example it can be placed inside the malariasim toolkit."

## Initial steps

1. Design a GitHub Action that, on PRs touching `mal-core/src/mal_core/abm/`
   (or `model_constants.yaml`), runs an agent that updates the ODD `.tex`
   and posts/commits the diff.
2. Add a short intro paragraph explaining the seven ODD 2010 Elements
   (Purpose; Entities, state variables, scales; Process overview; Design
   concepts; Initialization; Input data; Submodels).
3. Restructure `papers/`: remove from the repo, keep a generation tool
   (candidate: inside the `malariasim` toolkit) and treat the ODD
   bibliography as its input. For this docling must be used as the library
   that allows to process PDFs into markdown. As test the results must be
   equivalent to the actual papers folder, till this is not achieved the
   folder can not be removed.

## Dependencies / open points

- Removing `papers/` touches shared content — verify no other agent/session
  depends on it before deletion (repo rule: copy before delete).
- Action needs an agent runner with repo credentials; decide cost/trigger policy.
