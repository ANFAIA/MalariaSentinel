"""Tests for the tools of the agentic documentation review.

Three tools, three kinds of test:

* ``tools/redact_secrets.py`` — the leak gate. It must mask the whole
  credential and a truncated run of it, and it must find a credential in
  a tree and in a commit;
* ``tools/merge_agentic_reviews.py`` — the merger. It must read the
  findings array out of a report, fold the findings that two lenses
  reported the same way, and never invent a finding;
* ``tools/agentic_review_context.py`` — the context builder. Its pure
  parts (the classification of a path, the stage it belongs to, the
  comment lines of a diff) are pinned here; the rest is exercised by
  running it over the repository.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

SECRET = "oc_sk_0123456789abcdefghijklmnopqrstuvwxyz"


def _load(name: str, tool: str):
    path = REPO / "tools" / tool
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# the leak gate
# --------------------------------------------------------------------------


def test_the_whole_secret_is_masked():
    redact = _load("t_redact", "redact_secrets.py")
    text = f"the key is {SECRET} and that is all"
    out, hits = redact.redact_text(text, SECRET)
    assert SECRET not in out
    assert hits == 1
    assert "REDACTED" in out


def test_a_truncated_secret_is_masked():
    """A leaked prefix is still a leaked prefix."""
    redact = _load("t_redact", "redact_secrets.py")
    prefix = SECRET[:16]
    out, hits = redact.redact_text(f"key={prefix}", SECRET)
    assert prefix not in out
    assert hits == 1


def test_a_short_run_is_not_masked():
    """Six characters are not a credential; masking them would destroy the text."""
    redact = _load("t_redact", "redact_secrets.py")
    out, hits = redact.redact_text("the word oc_sk appears", SECRET)
    assert hits == 0
    assert out == "the word oc_sk appears"


def test_the_tree_scan_finds_the_leak(tmp_path):
    redact = _load("t_redact", "redact_secrets.py")
    (tmp_path / "clean.py").write_text("nothing here\n", encoding="utf-8")
    (tmp_path / "leaky.py").write_text(f'KEY = "{SECRET}"\n', encoding="utf-8")
    leaks = redact.scan_tree(tmp_path, SECRET)
    assert leaks == ["leaky.py"]


def test_the_history_scan_finds_the_leak(tmp_path):
    redact = _load("t_redact", "redact_secrets.py")
    repo = tmp_path / "repo"
    repo.mkdir()
    run = lambda *args: subprocess.run(  # noqa: E731
        args, cwd=repo, capture_output=True, text=True, check=True
    )
    run("git", "init", "-q")
    run("git", "config", "user.email", "t@example.invalid")
    run("git", "config", "user.name", "test")
    (repo / "file.py").write_text(f'KEY = "{SECRET}"\n', encoding="utf-8")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "a commit with a credential in it")
    leaks = redact.scan_history(SECRET, repo=repo)
    assert len(leaks) == 1


# --------------------------------------------------------------------------
# the merger
# --------------------------------------------------------------------------


def _report(text: str) -> str:
    return f"Some prose about the change.\n\n```json\n{text}\n```\n"


def test_the_findings_are_read_out_of_the_report():
    merge = _load("t_merge", "merge_agentic_reviews.py")
    prose, findings = merge.parse_report(
        _report(json.dumps([{"title": "a", "severity": "low", "file": "f.py", "line": 1}]))
    )
    assert "Some prose" in prose
    assert len(findings) == 1
    assert findings[0]["title"] == "a"


def test_a_report_without_an_array_yields_nothing():
    merge = _load("t_merge", "merge_agentic_reviews.py")
    prose, findings = merge.parse_report("Only prose, no array.")
    assert findings == []
    assert "Only prose" in prose


def test_a_broken_array_yields_nothing_rather_than_an_error():
    merge = _load("t_merge", "merge_agentic_reviews.py")
    _, findings = merge.parse_report("```json\n{not json}\n```\n")
    assert findings == []


def test_the_same_finding_from_two_lenses_is_one_finding():
    merge = _load("t_merge", "merge_agentic_reviews.py")
    finding = {
        "title": "the docstring says the function returns the array",
        "severity": "medium",
        "file": "a.py",
        "line": 10,
        "evidence": "the code assigns and returns nothing",
        "impact": "a reader expects a value",
    }
    other = {
        "title": "the docstring claims the function returns the array",
        "severity": "high",
        "file": "a.py",
        "line": 10,
        "evidence": "there is no return statement",
        "impact": "the caller gets None",
    }
    _, findings = merge.merge({"documentation": _report(json.dumps([finding])),
                               "structure": _report(json.dumps([other]))})
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"
    assert findings[0]["lenses"] == ["documentation", "structure"]


def test_different_findings_are_kept_apart():
    merge = _load("t_merge", "merge_agentic_reviews.py")
    left = {"title": "the channel order is wrong", "severity": "high",
            "file": "a.py", "line": 10}
    right = {"title": "the checkpoint is the last epoch", "severity": "low",
             "file": "b.py", "line": 3}
    _, findings = merge.merge({"documentation": _report(json.dumps([left])),
                               "claims": _report(json.dumps([right]))})
    assert len(findings) == 2


def test_the_comment_carries_the_marker_and_the_findings():
    merge = _load("t_merge", "merge_agentic_reviews.py")
    finding = {"title": "a defect", "severity": "high", "file": "a.py",
               "line": 10, "evidence": "e", "impact": "i"}
    prose, findings = merge.merge({"documentation": _report(json.dumps([finding]))})
    comment = merge.comment_text(prose, findings)
    assert comment.startswith("<!-- agentic-doc-review -->")
    assert "advisory" in comment
    assert "a defect" in comment


def test_an_empty_review_still_produces_a_comment():
    merge = _load("t_merge", "merge_agentic_reviews.py")
    prose, findings = merge.merge({"documentation": "", "structure": ""})
    comment = merge.comment_text(prose, findings)
    assert "the reviewer returned nothing" in comment
    assert "None." in comment


# --------------------------------------------------------------------------
# the context builder
# --------------------------------------------------------------------------


def test_a_path_is_classified_by_what_it_is():
    context = _load("t_context", "agentic_review_context.py")
    assert context.classify("mal-core/src/mal_core/cli.py") == "python"
    assert context.classify("mal-core/tests/test_cli.py") == "test"
    assert context.classify("mal-core/src/mal_core/abm/src/engine.cpp") == "cpp"
    assert context.classify("mal-core/config/model_constants.yaml") == "config"
    assert context.classify("docs/concepts/abm/odd-2010-malariasentinel.tex") == "document"


def test_a_path_is_matched_to_its_stage_and_its_document():
    context = _load("t_context", "agentic_review_context.py")
    assert context.stage_for("mal-core/src/mal_core/training/dataset.py") == "training"
    assert context.stage_for("mal-core/src/mal_core/scoring/registry.py") == "scoring"
    assert context.stage_for("mal-commonlib/src/mal_commonlib/data/loaders/smap.py") == "download"
    document = context.candidate_document("mal-core/src/mal_core/training/dataset.py")
    assert document == "docs/concepts/training/training.tex"


def test_the_comment_lines_of_a_diff_are_separated():
    context = _load("t_context", "agentic_review_context.py")
    diff = (
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1 +1 @@\n"
        "+# a new comment\n"
        "+value = 1\n"
        "-# an old comment\n"
        "-value = 2\n"
    )
    added, removed = context.comment_lines(diff)
    assert added == ["# a new comment"]
    assert removed == ["# an old comment"]


def test_a_macro_call_is_not_prose():
    context = _load("t_context", "agentic_review_context.py")
    text = "the basal survival is \\mskey{adults.mort_basal} and the floor is 0.60"
    prose = context._without_macros(text)
    assert "0.60" in prose
    assert "mskey" not in prose


# --------------------------------------------------------------------------
# the gate in the workflow, and the tool: the same masking
# --------------------------------------------------------------------------


def _workflow_gate_mask(secret: str):
    """The masking function of the workflow's leak gate, extracted."""
    import yaml

    workflow = REPO / ".github" / "workflows" / "agentic-doc-review.yml"
    document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    steps = document["jobs"]["review"]["steps"]
    for step in steps:
        run = step.get("run") or ""
        if "<<'PY'" not in run:
            continue
        body = run.split("<<'PY'\n", 1)[1].rsplit("PY\n", 1)[0]
        namespace: dict = {}
        # The gate is a script; only its masking function is needed, and
        # it reads the credential from the environment it runs in.
        source = body.split("leaked = False", 1)[0]
        os.environ["OPENCODE_API_KEY"] = secret
        os.environ.setdefault("RUNNER_TEMP", "/tmp")
        try:
            exec(compile(source, "leak-gate", "exec"), namespace)  # noqa: S102
        finally:
            os.environ.pop("OPENCODE_API_KEY", None)
        return namespace["mask"]
    raise AssertionError("the workflow has no leak gate")


def test_the_gate_and_the_tool_mask_the_same_way():
    """The gate is written in the workflow on purpose: it must not drift."""
    redact = _load("t_redact", "redact_secrets.py")
    secret = "oc_sk_0123456789abcdefghijklmnopqrstuvwxyz"
    mask = _workflow_gate_mask(secret)
    secret = "oc_sk_0123456789abcdefghijklmnopqrstuvwxyz"
    for text in (
        f"the key is {secret}",
        f"a prefix {secret[:16]} and the rest",
        f"nothing to hide here",
        f"two {secret} and {secret[:20]}",
    ):
        by_tool, tool_hits = redact.redact_text(text, secret)
        by_gate, gate_hits = mask(text)
        assert by_tool == by_gate, f"the two disagree on {text!r}"
        assert tool_hits == gate_hits, f"the two count differently on {text!r}"
        assert secret not in by_gate

