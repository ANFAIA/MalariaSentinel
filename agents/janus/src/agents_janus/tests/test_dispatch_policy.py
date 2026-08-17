"""Tests for dispatch path and child-task policy."""
from __future__ import annotations

from types import SimpleNamespace

from agents_janus.middleware.dispatch_policy import (
    DispatchPathMiddleware,
    normalize_gawt_paths,
)


def test_normalize_gawt_paths_strips_leading_slash():
    text = 'Edit "/test/collision_test.txt" line 1.'
    assert normalize_gawt_paths(text) == 'Edit "test/collision_test.txt" line 1.'


def test_normalize_gawt_paths_keeps_urls():
    text = "Read https://example.org/docs/index.html"
    assert normalize_gawt_paths(text) == text


def test_dispatch_middleware_rewrites_only_task_description():
    request = SimpleNamespace(
        tool_call={
            "name": "task",
            "args": {"description": "Edit /test/collision_test.txt"},
        },
    )
    request.override = lambda **kwargs: SimpleNamespace(**kwargs)

    rewritten = DispatchPathMiddleware._rewrite(request)

    assert rewritten.tool_call["args"]["description"] == (
        "Edit test/collision_test.txt"
    )
