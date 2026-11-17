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

The same run, on the same machine, with the same inputs. Locally there
is no OIDC: the credential is a personal key, taken from pi's own
credentials, and it never leaves the machine.

```bash
# the credential: pi's own key for the provider
export OPENCODE_API_KEY=$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.pi/agent/auth.json')))['opencode-go']['key'])")

# a clean agent directory with the provider's models declared
export PI_CODING_AGENT_DIR=$(mktemp -d)
mkdir -p "$PI_CODING_AGENT_DIR"
cp .github/agentic-reviewers/models.json "$PI_CODING_AGENT_DIR/models.json"

# the context
python3 tools/agentic_review_context.py \
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
python3 tools/redact_secrets.py --secret-env OPENCODE_API_KEY --file /tmp/report.md

# the merge
python3 tools/merge_agentic_reviews.py \
    --report documentation=/tmp/report.md \
    --out-comment /tmp/comment.md --out-findings /tmp/findings.json
```

The provider is declared in `.github/agentic-reviewers/models.json`:
the endpoint, the models, and the environment variable the credential
comes from. The file holds **no credential** — only the name of the
variable.

## The credential, and how it is kept

The review needs a model. There is **no stored credential**: the
repository holds no key at all.

The provider issues the credential per run. The workflow proves its
identity with the **OIDC token that GitHub issues to the job** (the job
holds `id-token: write`), and exchanges it for an access token that
**lasts an hour** and behaves like an API key:

```bash
oidc=$(curl -sSf --oauth2-bearer "$ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
  "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=https://opencode.ai/console" | jq -r .value)
token=$(curl -sSf https://opencode.ai/console/auth/oauth/token \
  -d grant_type=urn:ietf:params:oauth:grant-type:token-exchange \
  -d subject_token_type=urn:ietf:params:oauth:token-type:jwt \
  -d client_id=<the service account's public client id> \
  -d subject_token="$oidc" | jq -r .access_token)
echo "::add-mask::$token"
echo "OPENCODE_API_KEY=$token" >> "$GITHUB_ENV"
```

The **client id** (`sk_a0a294d9-…`) is the service account's public
identifier, not a secret: the authentication is the OIDC token itself,
and the client id can live in the workflow file. The service account is
configured in the provider's console for one repository, with read-only
permissions, a model scope, and an optional spending cap.

The model is chosen by the repository variable `AGENTIC_REVIEW_MODEL`;
the endpoint and the models are declared twice — in the workflow, which
is what runs, and in the file a local run uses — and the drift guard
keeps the two the same. Neither copy holds a credential: only the name
of the environment variable pi reads.

The measures that keep the credential from reaching a reader, in the
order they matter:

1. **There is nothing to leak.** The credential is minted per run and
   dies in an hour. The repository stores no key, so there is no key to
   steal from the repository's settings, no key to rotate after a leak,
   and no key in the history of the branch.
2. **The workflow that runs is the base branch's.** The trigger is
   `pull_request_target`, not `pull_request`: GitHub runs the workflow
   file of the **base** branch, so a pull request cannot change the
   sign-in step, the provider, the prompts, the gate, or the scripts
   that run with the credential. (With `pull_request`, the workflow that
   runs is the pull request's — the pull request could replace the gate
   with a gate that always passes.)
3. **Nothing from the pull request is executed.** The context builder,
   the signals helper and the two reviewer prompts are taken from the
   base branch with `git show`, which writes them out without running
   them. The pull request's files are only **read**: by a model with
   read-only tools, and by the leak gate.
4. **The provider is written by the workflow, not read from the tree.**
   The definition of the endpoint, the models and the credential's
   source is a heredoc in the workflow file, so a pull request cannot
   redirect the endpoint the credential is sent to. The file
   `.github/agentic-reviewers/models.json` is the copy a *local* run
   uses; `tools/check_agentic_models.py` fails when the two drift
   apart, and a test runs it.
5. **The credential is in the environment of two steps** — the reviewer
   and the gate, which needs it to mask what the reviewer produced — and
   no code from the pull request runs in either.
6. **The leak gate is written in the workflow**, not in the repository's
   `tools/`: the code that handles the credential must not be code the
   pull request can change. It masks the credential in everything the
   reviewer produced, and it records a verdict: the credential was
   found in the working tree or in the history, or it was not. Its
   logic is mirrored, and tested, in `tools/redact_secrets.py`, for use
   outside CI.
7. **The verdict is loud.** The gate's verdict is a job of its own,
   without `continue-on-error`: a leak turns the **run** red, and the
   job that posts the comment only runs when the verdict is clean. A
   leak therefore never reaches a reader *and* never passes unnoticed.
8. **The artefact is the redacted report.** The comment, the artefact
   and the log all carry the redacted text, and the token is masked in
   the log by `::add-mask::`.
9. **The checkout does not persist its token**, and the permissions are
   `contents: read`, `id-token: write` (the review job) and
   `pull-requests: write` (the job that posts the comment).
10. **A truncated credential counts as a leak.** The gate masks the
    whole credential and every contiguous run of twelve characters or
    more of it, extending the match as far as the text and the
    credential agree.

What these measures do **not** do:

* They do not protect against a change to the **base branch's** workflow
  that a maintainer merges: the ruleset should require an approval for
  the workflow files, as it does for the code.
* They do not protect against a prompt injection through the diff: the
  reviewer reads the pull request's content, and a malicious change can
  try to make it say something else. The credential is not in the
  model's context, the model has no tool that reaches the network or
  the shell, and the gate still holds the verdict.
* They do not limit what the credential can be used for. A key of a paid
  service is a key of a paid service: the spending cap belongs to the
  service account, in the provider's console.
* They do not protect the **model** from the content it reads. The
  reviewer sees the diff of the pull request; that is the point, and it
  is also the reason the reviewer runs with read-only tools.

One window remains, and it is this pull request's own: until the
machinery is merged, the base branch has no `tools/agentic_review_context.py`
and no reviewer prompt, so the workflow falls back to the pull request's
copy and says so in the log. The window closes when this pull request is
merged, and the fallback never runs again.

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

The first run over a real pull request — this layer's own pull request —
found **ten findings**, and all ten were real: three of them were holes
in the review's own security claims (the provider's endpoint came from
the tree the pull request controlled; the workflow that ran was the pull
request's own; the gate could not fail the run), and seven were
documentation defects the mechanical gates had missed (a contract table
that declared a no-data sentinel two artefacts do not carry, a variable
list two planes short of the file's, a docstring that promised a
randomisation no code performs, a README that described a module and a
package that no longer exist, and a module docstring that did not
describe the module). Every one of them was fixed in the same pull
request.

Before that, one reference change and one lens pair, by hand: the
documentation lens found three defects in a single added docstring — one
of them the docstring shadowing the accurate one that was already there
— and the structure lens found the same defects from the other side and
correctly concluded that no conceptual document had gone stale.

The false-positive rate is **one pull request old**. The measurement is
the same one the coherence review states: for each finding, whether a
human confirmed it, over a population of merges. The artefact
`agentic-findings` carries the merged findings of every run, so the
population can be collected once the reviews have run on real pull
requests.
