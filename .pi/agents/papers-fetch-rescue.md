---
name: papers-fetch-rescue
description: Fresh-session orchestrator for the paper corpus. Runs malariasim papers fetch; if papers remain pending_paywalled with open-licence candidates, launches the papers-rescue subagent, then reports.
tools: read, bash, Agent
run_in_background: false
---

You orchestrate the MalariaSentinel paper corpus fetch. Work from the repository root.

Requirements before you start:
- Load the private contact address in every shell you use:
  `set -a; . ~/.config/malariasim/papers.env; set +a`.
  The file is outside the repository. The address is private: never print it,
  copy it into a repository file, or include it in your report. If the file is
  missing, stop and tell the user; do not continue without it.

Steps:

1. Run the fetch. A non-zero exit code is a real error; stop and report it.
   ```bash
   set -a; . ~/.config/malariasim/papers.env; set +a; cd mal-core && uv run malariasim papers fetch 2>&1 | tee /tmp/papers-corpus/fetch-orchestrated.log
   ```
   Read the final line `fetch summary: ...`. Note the counts for ok, pending_paywalled,
   pending_no_source and pending_network.

2. If there are no `pending_paywalled` papers, skip to step 4.

3. Otherwise, list the rescuable papers and launch the rescue subagent:
   ```bash
   set -a; . ~/.config/malariasim/papers.env; set +a; cd mal-core && uv run malariasim papers rescue-list > /tmp/papers-corpus/rescue-list.json
   ```
   If the list is empty, skip to step 4. If it is not empty, launch the
   `papers-rescue` subagent with the Agent tool. Its brief must contain: the path
   `/tmp/papers-corpus/rescue-list.json`, the number of items, and the statement that
   it works only on open-licence candidates and stops at any barrier. Wait for its result.

4. Re-check the corpus and report:
   ```bash
   set -a; . ~/.config/malariasim/papers.env; set +a; cd mal-core && uv run malariasim papers fetch >/dev/null 2>&1; uv run malariasim papers check 2>&1 | tail -3
   ```
   (The second fetch is idempotent: papers already present are not downloaded again.)

Final report, under 250 words: the fetch summary before and after the rescue,
the papers the rescue adopted (ids), the barriers grouped by kind with counts, any
step that failed and why. Do not paste PDF content or the contact address.
