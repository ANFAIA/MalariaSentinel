# The agentic review: three readers, one comment

This file describes the **agentic documentation review**: a workflow that
runs three language-model reviewers over a pull request and posts one
advisory comment about what they found. It is the semantic half of the
review machinery; the mechanical half is `tools/coherence_signals.py`,
and the older, single-model review is `.github/workflows/coherence-review.yml`.

The question this review answers is narrow, and it is the question that
the mechanical signals cannot answer:

> **Is this change documented — and does the documentation that describes
> it still say what the code does?**

Everything else — whether the change is correct, whether it is
worthwhile, whether the tests pass — is somebody else's job.

## The three lenses

The reviewers are the same harness this repository's agents use (pi),
with read-only tools: `read`, `grep`, `find`, `ls`. They cannot write to
the tree and they cannot run commands. Each one gets a different
question, and each one is told what is *not* its question.

| lens | the file | the question |
|---|---|---|
| documentation | `.github/agentic-reviewers/documentation.md` | is the change documented by the code's own docstrings and comments? |
| structure | `.github/agentic-reviewers/structure.md` | does a structural change have the LaTeX that states it? |
| claims | `.github/agentic-reviewers/claims.md` | does the code do what its comments claim? |

The three share `.github/agentic-reviewers/common.md`, which states the
posture (an advisor, never a gate), the output format, and the rule
that a false positive costs more than a missed defect.

## The posture

* **It never blocks.** The job carries `continue-on-error: true`; the
  workflow never becomes a required check; a reviewer that fails, hangs
  or is skipped leaves the pull request green.
* **A signal is a candidate, not a finding.** The context builder
  produces mechanical signals — an entity whose code changed and whose
  docstring did not, a document that writes a number by hand that the
  code has moved. The reviewers are told to verify each one against the
  code, and most of them are noise.
* **A finding is what survived.** It carries a severity, a file, a line,
  the evidence, and the impact. The comment says which lens found it,
  and the findings that two lenses reported the same way are folded into
  one.

## What it costs

Three model runs per pull request. On the reference change — a single
docstring added to one function — the documentation lens took 1 m 43 s
and the structure lens 5 m 48 s. The context is small (32 kB for that
change) and the model is the cheapest one the provider offers
(`mimo-v2.6-flash` by default). The three lenses run in parallel, so
the wall-clock cost is the slowest lens.

## The context

`tools/agentic_review_context.py` builds what the reviewers read. It is
deterministic: the same pull request produces the same context.

1. **The shape of the pull request** — every changed file, its kind
   (code, test, configuration, document, prose), the stage it belongs to
   and the conceptual document that covers it.
2. **The diff** of the code and the configuration, capped per file and
   in total.
3. **The documentation the diff carries** — the comment lines it adds and
   removes.
4. **The mechanical signals** — the Python entities whose code changed
   and whose docstring did not (or was not there at all); the C++
   declarations whose comment did not change; the documents that write a
   moved value by hand rather than through a macro.
5. **The documents and their sections**, so a reviewer can name the
   section a change invalidates instead of saying "somewhere in the
   document".

## Running it locally

The same run, on the same machine, with the same inputs:

```bash
# the credential: the key of the provider the review uses
export OPENCODE_API_KEY=...            # never in the repository, never in the shell history

# a clean agent directory with the provider's models declared
export PI_CODING_AGENT_DIR=$(mktemp -d)
mkdir -p "$PI_CODING_AGENT_DIR"
cp .github/agentic-reviewers/models.json "$PI_CODING_AGENT_DIR/models.json"

# the context
python tools/agentic_review_context.py \
    --base origin/main --head HEAD --out /tmp/context.md

# one lens
pi --print \
    --no-session --no-extensions --no-skills --no-prompt-templates --no-mcp \
    --approve \
    --tools read,grep,find,ls \
    --provider opencode-go-ci --model mimo-v2.6-flash --thinking low \
    "@.github/agentic-reviewers/common.md" \
    "@.github/agentic-reviewers/documentation.md" \
    "@/tmp/context.md" \
    "Do the review now, and follow the output format the instructions give." \
    > /tmp/report.md 2>/tmp/pi.err

# the leak gate, before the report is read by anybody
python tools/redact_secrets.py --secret-env OPENCODE_API_KEY --file /tmp/report.md

# the merge
python tools/merge_agentic_reviews.py \
    --report documentation=/tmp/report.md \
    --out-comment /tmp/comment.md --out-findings /tmp/findings.json
```

The provider is declared in `.github/agentic-reviewers/models.json`:
the endpoint, the models, and the environment variable the credential
comes from. The file holds **no credential** — only the name of the
variable.

## The credential, and how it is kept

The review needs a model. The credential is the repository secret
`OPENCODE_API_KEY`; the model is chosen by the repository variable
`AGENTIC_REVIEW_MODEL`; the endpoint and the models are declared in
`.github/agentic-reviewers/models.json`.

The credential is a key of a paid service, so the review is built so
that the key cannot reach a reader. The measures, in the order they
matter:

1. **A fork's pull request never receives a secret.** The trigger is
   `pull_request`, never `pull_request_target`. GitHub gives no secret
   to a pull request from a fork, so the reviewer there is simply
   skipped, and the mechanical part of the review still runs.
2. **The credential is in the environment of one step only**, and no
   code from the pull request runs in that step. The reviewer is pi's
   own binary, installed from npm in the step before.
3. **The leak gate is written in the workflow**, not in the repository's
   `tools/`: the code that handles the credential must not be code the
   pull request can change. It masks the credential in everything the
   reviewer produced, and it fails the run when the credential is found
   in the working tree or in the history. Its logic is mirrored, and
   tested, in `tools/redact_secrets.py`, for use outside CI.
4. **The artefact is the redacted report.** The comment, the artefact
   and the log all carry the redacted text.
5. **The checkout does not persist its token**, and the permissions are
   `contents: read` and `pull-requests: write`.
6. **A truncated credential counts as a leak.** The gate masks the whole
   credential and every contiguous run of twelve characters or more of
   it, extending the match as far as the text and the credential agree.

What these measures do **not** do:

* They do not protect against a pull request that changes the workflow
  itself. The workflow lives in the repository, so a branch can change
  it; a fork's pull request cannot obtain the secret, but a branch
  inside the repository could. The repository's ruleset should require
  an approval for the workflow files — the same policy as for the code.
* They do not protect the key from a maintainer who reads the CI
  configuration. It is not printed anywhere; it is not in the log.
* They do not limit what the credential can be used for. A key of a paid
  service is a key of a paid service: if it leaks, it leaks. A
  dedicated key for the review, with a spending limit, is the
  remaining measure, and it belongs to whoever holds the account.

## What it is not

* It is not a gate. Nothing it says blocks a merge.
* It is not a substitute for the mechanical gates: `tools/check_docstrings.py`
  proves that every published entity has a docstring, and the LaTeX
  build proves that every `\mskey{}` exists. Those are deterministic and
  they are cheap; the agentic review is for what they cannot see.
* It is not the coherence review. That one compares the documents with
  the code as a whole; this one reads the change and its
  documentation.

## What has been measured

So far: one reference change, one lens pair, by hand. The documentation
lens found three defects in a single added docstring — one of them the
docstring shadowing the accurate one that was already there — and the
structure lens found the same defects from the other side and correctly
concluded that no conceptual document had gone stale.

The false-positive rate of the three lenses is **not measured**. The
measurement is the same one the coherence review states: for each
finding, whether a human confirmed it, over a population of merges. The
artefact `agentic-findings` carries the merged findings of every run, so
the population can be collected once the reviews have run on real pull
requests.
