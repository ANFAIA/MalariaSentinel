"""Tests for MCP persistent session pool in mcp_bridge.

Verifies that sessions are reused across tool calls (avoiding cold-start
overhead) and that stale sessions are correctly invalidated and recreated.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_janus.mcp_bridge import (
    _ensure_loop_thread,
    _get_or_create_session,
    _invalidate_session,
    _session_pool,
    shutdown_all_sessions,
)


@pytest.fixture(autouse=True)
def _clean_pool():
    """Clear session pool before and after each test."""
    _session_pool.clear()
    yield
    _session_pool.clear()


def _make_mock_session():
    """Create a mock ClientSession with a working call_tool."""
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    block = MagicMock()
    block.text = '{"ok": true}'
    result = MagicMock()
    result.content = [block]
    session.call_tool = AsyncMock(return_value=result)
    return session


def _make_fake_stdio():
    """Return a fake stdio_client context manager factory."""

    @asynccontextmanager
    async def fake_stdio_client(params):
        yield (MagicMock(), MagicMock())

    return fake_stdio_client


def test_session_reuse_across_calls():
    """Second call to same server must NOT create a new stdio_client."""
    mock_session = _make_mock_session()
    fake_stdio = _make_fake_stdio()
    bt = _ensure_loop_thread()

    async def _test():
        with patch("mcp.client.stdio.stdio_client", side_effect=fake_stdio):
            with patch("mcp.ClientSession", return_value=mock_session):
                from mcp import StdioServerParameters
                params = StdioServerParameters(command="echo", args=["test"])

                # First call — cold start
                pooled1 = await _get_or_create_session("test_server", params)
                assert pooled1.session is mock_session
                assert "test_server" in _session_pool

                # Second call — must reuse same session
                pooled2 = await _get_or_create_session("test_server", params)
                assert pooled2.session is mock_session
                assert pooled1 is pooled2  # same object

    future = asyncio.run_coroutine_threadsafe(_test(), bt.loop)
    future.result(timeout=10)


def test_concurrent_servers_independent():
    """Different servers get independent sessions."""
    fake_stdio = _make_fake_stdio()
    bt = _ensure_loop_thread()

    async def _test():
        with patch("mcp.client.stdio.stdio_client", side_effect=fake_stdio):
            with patch("mcp.ClientSession") as mock_cs:
                mock_cs.return_value = _make_mock_session()
                from mcp import StdioServerParameters

                params_a = StdioServerParameters(command="echo", args=["a"])
                params_b = StdioServerParameters(command="echo", args=["b"])

                pooled_a = await _get_or_create_session("server_a", params_a)
                pooled_b = await _get_or_create_session("server_b", params_b)

                assert pooled_a is not pooled_b
                assert len(_session_pool) == 2

    future = asyncio.run_coroutine_threadsafe(_test(), bt.loop)
    future.result(timeout=10)


def test_invalidate_and_recreate():
    """Invalidating a session allows fresh creation on next call."""
    fake_stdio = _make_fake_stdio()
    bt = _ensure_loop_thread()

    async def _test():
        with patch("mcp.client.stdio.stdio_client", side_effect=fake_stdio):
            with patch("mcp.ClientSession") as mock_cs:
                mock_cs.return_value = _make_mock_session()
                from mcp import StdioServerParameters
                params = StdioServerParameters(command="echo", args=["test"])

                # Create session
                await _get_or_create_session("test_server", params)
                assert "test_server" in _session_pool

                # Invalidate
                _invalidate_session("test_server")
                assert "test_server" not in _session_pool

                # Recreate
                pooled = await _get_or_create_session("test_server", params)
                assert "test_server" in _session_pool
                assert pooled.session is not None

    future = asyncio.run_coroutine_threadsafe(_test(), bt.loop)
    future.result(timeout=10)


def test_background_loop_singleton():
    """_ensure_loop_thread returns the same thread instance."""
    bt1 = _ensure_loop_thread()
    bt2 = _ensure_loop_thread()
    assert bt1 is bt2
    assert bt1.loop.is_running()


def test_shutdown_clears_pool():
    """shutdown_all_sessions empties the pool."""
    bt = _ensure_loop_thread()

    async def _test():
        fake_stdio = _make_fake_stdio()
        with patch("mcp.client.stdio.stdio_client", side_effect=fake_stdio):
            with patch("mcp.ClientSession") as mock_cs:
                mock_cs.return_value = _make_mock_session()
                from mcp import StdioServerParameters
                params = StdioServerParameters(command="echo", args=["test"])

                # Create a session in the pool
                await _get_or_create_session("test_server", params)
                assert "test_server" in _session_pool

                # shutdown_all_sessions should remove it
                shutdown_all_sessions()
                assert "test_server" not in _session_pool

    future = asyncio.run_coroutine_threadsafe(_test(), bt.loop)
    future.result(timeout=10)
