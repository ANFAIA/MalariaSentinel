"""LLM scorer — qualitative verdict on a 10-dimension calibration report.

This module is the calibration framework's "qualitative judge". After the
10 deterministic scorers (D1..D10) run on an ABM rollout, the same report
(JSON) is sent to a small LLM via the OpenCode Zen chat/completions API.
The LLM returns a structured :class:`Verdict` (viable / borderline /
regressed / collapsed) plus a list of concerns, recommendations, and
literature grounding.

The LLM is invoked directly via :mod:`langchain_openai` — there is no
OpenCode harness, no agent loop, no project knowledge graph. The scorer
runs in ~1-3 seconds, is deterministic at temperature 0, and is
content-hash-cached so repeated runs against the same report are free.

If the LLM call fails for any reason (missing key, network error, schema
validation failure, timeout), the module falls back to
:func:`deterministic_fallback`, which returns a `verdict="unknown"`
response so the rest of the pipeline can keep moving.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
"""Base URL for the OpenRouter chat/completions endpoint."""

LLM_MODEL_DEFAULT: str = "minimax/minimax-m3"
"""Default model id on OpenRouter."""

LLM_TIMEOUT_S: int = 180
"""Per-request timeout in seconds. Tuned for the worst case (long report
+ cold cache + structured-output negotiation)."""

LLM_CACHE_DIRNAME: str = ".cache/llm_verdicts"
"""Cache directory (relative to the calibration run root). One file per
content-hash. Cache writes are JSON; the cache is safe to delete at any
time."""

# Path to the bundled system-prompt markdown. Resolved at import time so
# that subsequent calls do not hit the filesystem.
_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "llm_verdict.md"
SYSTEM_PROMPT: str = _PROMPT_PATH.read_text(encoding="utf-8")
"""The full system prompt (charter + reference ranges + output rules).
Loaded from ``scorers/prompts/llm_verdict.md`` at import time."""


# ---------------------------------------------------------------------------
# Pydantic schema — the LLM's structured output
# ---------------------------------------------------------------------------


class Verdict(BaseModel):
    """Structured LLM verdict on a calibration report."""

    verdict: Literal["viable", "borderline", "regressed", "collapsed"]
    """One of the four qualitative categories. ``unknown`` is reserved for
    the deterministic fallback and is not a valid LLM response."""

    composite_estimate: float = Field(ge=0.0, le=1.0)
    """The LLM's holistic read of the report, in [0.0, 1.0]. Allowed to
    deviate from the deterministic composite by up to 0.10."""

    concerns: list[str] = Field(default_factory=list)
    """Specific dimensions that are out-of-range or suspicious. Each entry
    should cite the dimension id (e.g. ``D1``) and the observed value."""

    recommendations: list[str] = Field(default_factory=list)
    """Concrete, runnable actions a human or another agent can take to
    address the concerns."""

    literature_grounding: list[str] = Field(default_factory=list)
    """One short sentence per paper / source the LLM relied on. In-text
    citation in parentheses, e.g. ``Mordecai 2013``."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _report_hash(report: dict[str, Any], model: str) -> str:
    """Stable content hash of a report, for the LLM verdict cache.

    The hash is over the JSON-serialised report plus the model id, so
    switching models invalidates the cache (intentional: a different
    model may give a different verdict on the same report).

    Args:
        report: The calibration report dict.
        model: The LLM model id used for the call.

    Returns:
        A hex sha256 digest (64 chars). Used as the cache filename.
    """
    payload = json.dumps(
        {"model": model, "report": report},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_api_key() -> str | None:
    """Resolve the OpenRouter API key from the environment.

    Order of precedence:
    1. ``OPENROUTER_KEY`` already in ``os.environ`` (covers shell exports
       and CI).
    2. A ``.env`` file walked up from this file's directory (covers
       ``/Users/.../MalariaSentinel/.env`` and CI runners that mount
       the env file under the repo root).

    Args:
        None.

    Returns:
        The API key string, or ``None`` if not found.
    """
    env_key = os.environ.get("OPENROUTER_KEY")
    if env_key:
        return env_key

    here = Path(__file__).resolve().parent
    while True:
        candidate = here / ".env"
        if candidate.is_file():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == "OPENROUTER_KEY":
                    return v.strip().strip('"').strip("'") or None
            return None
        parent = here.parent
        if parent == here:
            break
        here = parent
    return None


def _cache_path(cache_root: Path, content_hash: str) -> Path:
    """Resolve the on-disk path for a cached verdict.

    Args:
        cache_root: The cache root directory (e.g. ``.cache/llm_verdicts``).
        content_hash: The sha256 hex digest from :func:`_report_hash`.

    Returns:
        The full path to the cache file (``<hash>.json``).
    """
    return cache_root / f"{content_hash}.json"


def _read_cache(cache_file: Path) -> dict[str, Any] | None:
    """Read a cached verdict from disk.

    Args:
        cache_file: The path to a cache file.

    Returns:
        The cached verdict dict, or ``None`` if the file is missing or
        unreadable.
    """
    if not cache_file.is_file():
        return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(cache_file: Path, verdict: dict[str, Any]) -> None:
    """Write a verdict to the cache.

    Args:
        cache_file: The path to write to.
        verdict: The verdict dict to serialise.

    Returns:
        None. Failures are swallowed — caching is best-effort.
    """
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(verdict, indent=2, default=str), encoding="utf-8")
    except OSError:
        return


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------


def deterministic_fallback(report: dict[str, Any], *, reason: str) -> dict[str, Any]:
    """Return a deterministic, non-LLM verdict when the LLM call fails.

    The fallback always reports ``verdict="unknown"`` and ``composite``
    equal to whatever the deterministic composite was. The ``fallback``
    field carries a human-readable reason so the user can debug.

    Args:
        report: The calibration report dict. The ``composite`` key is
            read if present.
        reason: A short description of why the LLM call failed (e.g.
            ``"OPENCODE_API_KEY not set"`` or ``"API timeout after 180s"``).

    Returns:
        A dict with the same shape as :class:`Verdict` plus a
        ``fallback`` field.
    """
    return {
        "verdict": "unknown",
        "composite_estimate": float(report.get("composite", 0.0)),
        "concerns": [],
        "recommendations": [],
        "literature_grounding": [],
        "fallback": reason,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def score_with_llm(
    report: dict[str, Any],
    *,
    model: str = LLM_MODEL_DEFAULT,
    cache_dir: Path | None = None,
    timeout_s: int = LLM_TIMEOUT_S,
) -> dict[str, Any]:
    """Score a calibration report with the LLM judge.

    The function:
    1. Computes a content hash of the report + model id.
    2. Checks the cache and returns a cached verdict if one exists.
    3. Resolves the OpenCode API key.
    4. Calls the OpenCode Zen ``chat/completions`` endpoint via
       :class:`langchain_openai.ChatOpenAI` with
       ``with_structured_output(Verdict)``.
    5. Caches the verdict and returns it.
    6. On any failure, returns :func:`deterministic_fallback`.

    Args:
        report: The calibration report dict. Typically contains
            ``experiment``, ``scores`` (D1..D10), ``composite``, etc.
        model: The model id to use. Defaults to
            :data:`LLM_MODEL_DEFAULT` (``"minimax-m3"``).
        cache_dir: Override the cache directory. Defaults to
            ``.cache/llm_verdicts`` under the current working directory.
        timeout_s: Per-request timeout in seconds.

    Returns:
        A dict matching :class:`Verdict`. On LLM failure, a dict
        matching :func:`deterministic_fallback` (with an extra
        ``fallback`` field).
    """
    # 1. Hash + cache lookup
    content_hash = _report_hash(report, model)
    cache_root = Path(cache_dir) if cache_dir is not None else Path(LLM_CACHE_DIRNAME)
    cache_file = _cache_path(cache_root, content_hash)
    cached = _read_cache(cache_file)
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    # 2. API key
    api_key = _load_api_key()
    if not api_key:
        return deterministic_fallback(report, reason="OPENROUTER_KEY not set")

    # 3. Call the OpenRouter API directly via requests + parse JSON response.

    try:
        import requests

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": model,
            "temperature": 0,
            "timeout": timeout_s,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Calibration report:\n```json\n{json.dumps(report, indent=2, default=str)}\n```\n\nReturn ONLY a JSON object matching this schema:\n{Verdict.model_json_schema()}"},
            ],
        }

        started = time.monotonic()
        resp = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        elapsed = time.monotonic() - started

        content = resp.json()["choices"][0]["message"]["content"]
        # Strip markdown fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

        parsed = json.loads(content)
        verdict_obj = Verdict(**parsed)
        verdict_dict = verdict_obj.model_dump()
        verdict_dict["latency_s"] = round(elapsed, 3)
        verdict_dict["model"] = model
        verdict_dict["cache_hit"] = False

        # 4. Cache + return
        _write_cache(cache_file, verdict_dict)
        return verdict_dict

    except ValidationError as exc:
        return deterministic_fallback(
            report,
            reason=f"LLM output failed Pydantic validation: {exc}",
        )
    except Exception as exc:  # noqa: BLE001 — any LLM/transport failure
        return deterministic_fallback(
            report,
            reason=f"LLM call failed: {type(exc).__name__}: {exc}",
        )
