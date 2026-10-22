"""Regression tests for tools/audit_comment_constants.py (task-04).

The round-2 reviewer found that the audit excluded any directory named
``data``, so the whole loader package (``mal_commonlib/data/loaders``) was
never scanned — the exact layer where the first leak had lived. These tests
pin the fix: a leak under ``.../data/loaders/`` must be reported just like
the same leak anywhere else, and lowercase assignments of YAML values must
be caught too.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "audit_comment_constants.py"
LEAK = '# adult mortality 0.87 per day\n"""Retired: RAIN_THRESHOLD_MM = 15."""\n'


def _audit():
    spec = importlib.util.spec_from_file_location("t04_audit", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tree(tmp_path: Path) -> Path:
    """Mirror the repo layout: a loader package plus an ordinary package."""
    for sub in ("mal-commonlib/src/mal_commonlib/data/loaders",
                "mal-commonlib/src/mal_commonlib/other"):
        directory = tmp_path / sub
        directory.mkdir(parents=True)
        (directory / "leak.py").write_text(LEAK, encoding="utf-8")
    return tmp_path


def test_data_loader_package_is_scanned(tmp_path, capsys):
    audit = _audit()
    rc = audit.main(["audit", str(_tree(tmp_path))])
    out = capsys.readouterr().out
    assert rc == 1
    assert "data/loaders/leak.py" in out
    assert "other/leak.py" in out
    # Both copies are reported; the historical bug reported only `other/`.
    assert out.count("leak.py:") >= 2


def test_lowercase_assignment_of_yaml_value_is_detected(tmp_path, capsys):
    audit = _audit()
    probe = tmp_path / "probe.py"
    probe.write_text("# foo = 0.87\n", encoding="utf-8")
    rc = audit.main(["audit", str(probe)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "assignment:foo=0.87" in out


def test_lowercase_assignment_of_non_yaml_value_is_quiet(tmp_path, capsys):
    audit = _audit()
    probe = tmp_path / "probe.py"
    probe.write_text("# foo = 987654\n", encoding="utf-8")
    rc = audit.main(["audit", str(probe)])
    assert rc == 0
