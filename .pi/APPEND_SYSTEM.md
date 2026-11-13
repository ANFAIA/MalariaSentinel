# EGM bundle root

The Elephant-Goldfish Model (EGM) bundle is vendored at `.pi/egm/` (relative to the project working directory). When any `egm-*` skill or EGM persona references `agents/`, `resources/`, or `docs/`, resolve those paths against `.pi/egm/` — not against the skill's own directory. EGM reviewer subagents are defined in `.pi/agents/egm-*.md`.
