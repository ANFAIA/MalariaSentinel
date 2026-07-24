"""Unit tests for ``scorers.llm_scorer``.

The tests in this file are pure unit tests — no network, no real LLM
calls. ``langchain_openai.ChatOpenAI`` is replaced with an in-process
mock via ``sys.modules`` injection (the scorer imports it lazily inside
``score_with_llm``), and the cache directory is redirected to a
``tmp_path`` fixture so each test gets a clean slate.

The contract under test:

- :class:`Verdict` accepts the four valid verdicts, rejects others, and
  pins ``composite_estimate`` to ``[0.0, 1.0]``.
- :func:`deterministic_fallback` always returns a dict with a
  ``fallback`` field carrying the reason, and inherits ``composite``
  from the input report.
- :func:`score_with_llm` is content-hash-cached, calls the LLM only on
  cache miss, falls back deterministically on LLM error, and
  instantiates ``ChatOpenAI`` with the documented parameters
  (``temperature=0``, ``base_url=https://opencode.ai/zen/v1``,
  ``model=minimax-m3``, ``timeout=180``) using
  ``with_structured_output(Verdict)``.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest
from pydantic import ValidationError

from scorers import llm_scorer
from scorers.llm_scorer import (
    LLM_BASE_URL,
    LLM_CACHE_DIRNAME,
    LLM_MODEL_DEFAULT,
    LLM_TIMEOUT_S,
    Verdict,
    deterministic_fallback,
    score_with_llm,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """An isolated cache directory for one test.

    Passed to ``score_with_llm(..., cache_dir=cache_dir)`` so the scorer
    never touches the working directory's ``.cache/llm_verdicts``.
    """
    d = tmp_path / "llm_verdicts"
    d.mkdir()
    return d


@pytest.fixture
def mock_chat_openai(monkeypatch: pytest.MonkeyPatch):
    """Inject a mock ``langchain_openai`` module and return a tracker.

    The mock provides a ``MockChatOpenAI`` class that:

    - Records every constructor call (kwargs) into ``tracker["init"]``.
    - Captures the schema passed to ``with_structured_output`` into
      ``tracker["schema"]``.
    - Captures every invoke payload into ``tracker["invoke"]`` and
      returns a Verdict from a queue (``tracker["responses"]``); if the
      next queue item is an ``Exception``, the mock raises it.

    Also sets ``OPENCODE_API_KEY`` so the function does not bail out on
    missing credentials.
    """
    tracker: dict = {"init": [], "schema": [], "invoke": [], "responses": []}

    class MockChatOpenAI:
        def __init__(self, **kwargs):
            tracker["init"].append(kwargs)

        def with_structured_output(self, schema):
            tracker["schema"].append(schema)
            return self

        def invoke(self, messages):
            tracker["invoke"].append(messages)
            if tracker["responses"]:
                action = tracker["responses"].pop(0)
                if isinstance(action, BaseException):
                    raise action
                return action
            return Verdict(
                verdict="viable",
                composite_estimate=0.85,
                concerns=[],
                recommendations=[],
                literature_grounding=[],
            )

    mock_module = types.ModuleType("langchain_openai")
    mock_module.ChatOpenAI = MockChatOpenAI

    monkeypatch.setitem(sys.modules, "langchain_openai", mock_module)
    monkeypatch.setenv("OPENCODE_API_KEY", "test-key-not-real")

    return tracker


# ---------------------------------------------------------------------------
# Verdict Pydantic schema
# ---------------------------------------------------------------------------


def test_verdict_schema_accepts_viable() -> None:
    """A well-formed Verdict round-trips through model_dump() losslessly."""
    v = Verdict(
        verdict="viable",
        composite_estimate=0.85,
        concerns=["D2 is high"],
        recommendations=["Re-run with lower initial prevalence"],
        literature_grounding=["Mordecai 2013"],
    )
    dumped = v.model_dump()
    assert dumped["verdict"] == "viable"
    assert dumped["composite_estimate"] == 0.85
    assert dumped["concerns"] == ["D2 is high"]
    assert dumped["recommendations"] == ["Re-run with lower initial prevalence"]
    assert dumped["literature_grounding"] == ["Mordecai 2013"]


def test_verdict_schema_rejects_invalid_verdict() -> None:
    """Verdict is a closed enum — anything outside the four valid values
    must raise ``ValidationError``."""
    with pytest.raises(ValidationError):
        Verdict(verdict="exploded", composite_estimate=0.5)


def test_verdict_schema_rejects_composite_above_1() -> None:
    """``composite_estimate`` is pinned to ``[0.0, 1.0]`` — anything
    above must raise ``ValidationError``."""
    with pytest.raises(ValidationError):
        Verdict(verdict="viable", composite_estimate=1.5)


def test_verdict_schema_rejects_composite_below_0() -> None:
    """``composite_estimate`` is pinned to ``[0.0, 1.0]`` — anything
    below must raise ``ValidationError``."""
    with pytest.raises(ValidationError):
        Verdict(verdict="viable", composite_estimate=-0.1)


# ---------------------------------------------------------------------------
# deterministic_fallback
# ---------------------------------------------------------------------------


def test_deterministic_fallback_includes_reason() -> None:
    """The fallback's ``fallback`` field carries the human-readable
    reason verbatim so the user can debug why the LLM path failed."""
    report = {"experiment": "test", "composite": 0.5}
    result = deterministic_fallback(report, reason="API timeout after 180s")
    assert result["fallback"] == "API timeout after 180s"
    assert result["verdict"] == "unknown"


def test_deterministic_fallback_inherits_composite() -> None:
    """The fallback inherits the deterministic composite from the
    report so downstream consumers do not lose that signal."""
    report = {"composite": 0.42, "experiment": "t"}
    result = deterministic_fallback(report, reason="OPENCODE_API_KEY not set")
    assert result["composite_estimate"] == 0.42
    assert result["verdict"] == "unknown"


# ---------------------------------------------------------------------------
# score_with_llm — cache behaviour
# ---------------------------------------------------------------------------


def test_score_with_llm_uses_cache(
    cache_dir: Path, mock_chat_openai: dict
) -> None:
    """When the cache file exists for the report, the LLM must NOT be
    called and the cached value is returned (annotated with
    ``cache_hit=True``)."""
    report = {"experiment": "test", "composite": 0.85, "scores": {"D1": 0.9}}
    cache_key = llm_scorer._report_hash(report, LLM_MODEL_DEFAULT)
    cached = {
        "verdict": "viable",
        "composite_estimate": 0.85,
        "concerns": [],
        "recommendations": [],
        "literature_grounding": [],
    }
    (cache_dir / f"{cache_key}.json").write_text(json.dumps(cached))

    result = score_with_llm(report, cache_dir=cache_dir)

    assert result["verdict"] == "viable"
    assert result.get("cache_hit") is True
    assert mock_chat_openai["init"] == []
    assert mock_chat_openai["invoke"] == []


def test_score_with_llm_calls_llm_on_cache_miss(
    cache_dir: Path, mock_chat_openai: dict
) -> None:
    """On a cache miss, the LLM is called exactly once, the verdict
    comes back, and a cache file is written for next time."""
    report = {"experiment": "test", "composite": 0.85}
    mock_chat_openai["responses"].append(
        Verdict(
            verdict="viable",
            composite_estimate=0.85,
            concerns=["D2 borderline"],
            recommendations=["Tune initial prevalence"],
            literature_grounding=["Mordecai 2013"],
        )
    )

    result = score_with_llm(report, cache_dir=cache_dir)

    assert result["verdict"] == "viable"
    assert result.get("cache_hit") is False
    assert result["composite_estimate"] == 0.85
    assert len(mock_chat_openai["init"]) == 1
    assert len(mock_chat_openai["invoke"]) == 1

    # The verdict was written to the cache.
    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) == 1
    on_disk = json.loads(cache_files[0].read_text())
    assert on_disk["verdict"] == "viable"


def test_score_with_llm_falls_back_on_llm_error(
    cache_dir: Path, mock_chat_openai: dict
) -> None:
    """If the LLM raises any exception, the deterministic fallback is
    returned with a ``fallback`` reason that includes the exception
    type and message."""
    report = {"experiment": "test", "composite": 0.5}
    mock_chat_openai["responses"].append(
        RuntimeError("simulated transport failure")
    )

    result = score_with_llm(report, cache_dir=cache_dir)

    assert result["verdict"] == "unknown"
    assert "fallback" in result
    assert "RuntimeError" in result["fallback"]
    assert "simulated transport failure" in result["fallback"]
    assert result["composite_estimate"] == 0.5


def test_cache_key_is_content_addressed(
    cache_dir: Path, mock_chat_openai: dict
) -> None:
    """Two reports that differ only in field order must hash to the
    same cache key, so the second call hits the cache and does not
    invoke the LLM."""
    report_a = {"a": 1, "b": 2, "c": 3, "composite": 0.7}
    report_b = {"c": 3, "b": 2, "a": 1, "composite": 0.7}  # same content, reordered

    mock_chat_openai["responses"].append(
        Verdict(verdict="viable", composite_estimate=0.8)
    )
    r1 = score_with_llm(report_a, cache_dir=cache_dir)
    r2 = score_with_llm(report_b, cache_dir=cache_dir)

    assert r1.get("cache_hit") is False
    assert r2.get("cache_hit") is True
    assert len(mock_chat_openai["init"]) == 1
    assert len(mock_chat_openai["invoke"]) == 1


# ---------------------------------------------------------------------------
# score_with_llm — ChatOpenAI instantiation contract
# ---------------------------------------------------------------------------


def test_temperature_zero_for_determinism(
    cache_dir: Path, mock_chat_openai: dict
) -> None:
    """The scorer must instantiate ChatOpenAI with ``temperature=0``
    so verdicts are reproducible across runs."""
    score_with_llm({"experiment": "t"}, cache_dir=cache_dir)

    assert len(mock_chat_openai["init"]) == 1
    assert mock_chat_openai["init"][0]["temperature"] == 0.0


def test_base_url_is_opencode_zen(
    cache_dir: Path, mock_chat_openai: dict
) -> None:
    """The scorer must point at the OpenCode Zen chat/completions
    endpoint — not at api.openai.com or anywhere else."""
    score_with_llm({"experiment": "t"}, cache_dir=cache_dir)

    assert mock_chat_openai["init"][0]["base_url"] == "https://opencode.ai/zen/v1"


def test_default_model_is_minimax_m3(
    cache_dir: Path, mock_chat_openai: dict
) -> None:
    """If the caller does not pass ``model=...``, the default
    ``minimax-m3`` must be used."""
    score_with_llm({"experiment": "t"}, cache_dir=cache_dir)

    assert mock_chat_openai["init"][0]["model"] == "minimax-m3"


def test_timeout_is_180s(cache_dir: Path, mock_chat_openai: dict) -> None:
    """The scorer must pass ``timeout=180`` to ChatOpenAI so a slow
    LLM does not hang the calibration run indefinitely."""
    score_with_llm({"experiment": "t"}, cache_dir=cache_dir)

    assert mock_chat_openai["init"][0]["timeout"] == 180


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


def test_module_constants_are_correct() -> None:
    """The four module-level constants are part of the scorer's public
    contract — downstream callers (config, runbooks) read them by
    name. Any change here is a breaking change for the calibration
    pipeline."""
    assert LLM_BASE_URL == "https://opencode.ai/zen/v1"
    assert LLM_MODEL_DEFAULT == "minimax-m3"
    assert LLM_TIMEOUT_S == 180
    assert LLM_CACHE_DIRNAME == ".cache/llm_verdicts"


# ---------------------------------------------------------------------------
# Structured-output contract
# ---------------------------------------------------------------------------


def test_pydantic_schema_is_used_for_structured_output(
    cache_dir: Path, mock_chat_openai: dict
) -> None:
    """The LLM response must be validated against the :class:`Verdict`
    Pydantic schema. The scorer wires that up via
    ``llm.with_structured_output(Verdict)`` — if that call is ever
    removed, the LLM would return a free-form dict and the calibration
    pipeline would silently break."""
    score_with_llm({"experiment": "t"}, cache_dir=cache_dir)

    assert len(mock_chat_openai["schema"]) == 1
    assert mock_chat_openai["schema"][0] is Verdict
