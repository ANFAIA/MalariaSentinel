"""MalariasimShellBackend — LocalShellBackend with shell restricted to `malariasim`.

deepagents exposes a built-in `execute` tool whenever the agent's backend
implements `SandboxBackendProtocol`. We reuse that built-in tool (no custom
tool) and restrict what it can run via a backend policy hook:

- `execute()` only accepts `malariasim` invocations (optionally via
  `uv run ...` / `python -m mal_core.cli`). Anything else is rejected.
- `read()` / `write()` / `edit()` replicate the filesystem deny rules that
  used to be expressed as `FilesystemPermission` (secrets unreadable, writes
  confined to the gawt worktree).

This is the documented "backend policy hooks" approach:
https://docs.langchain.com/oss/python/deepagents/backends#add-policy-hooks
"""
from __future__ import annotations

import fnmatch
import shlex

from deepagents.backends import LocalShellBackend
from deepagents.backends.protocol import (
    EditResult,
    ExecuteResponse,
    ReadResult,
    WriteResult,
)

# Paths that must never be readable (glob patterns, virtual paths).
_SECRET_READ_PATTERNS = (
    "/.env",
    "/**/.env",
    "/**/*secret*",
    "/**/*credential*",
)

# Writes are only allowed inside the gawt worktree; everything else is denied.
_WRITE_ALLOW_PATTERNS = (
    "/.gitagent/worktree/**",
)
_WRITE_DENY_PATTERNS = (
    "/data/**",
    "/.git/**",
)

# Tokens that would let a command escape the malariasim allowlist.
# Checked as characters so tokens like `--help;` or `x|y` are caught too.
_BANNED_SHELL_CHARS = (";", "|", "&", ">", "<", "`", "$", "\\", "\n")


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def _is_malariasim_command(command: str) -> bool:
    """Validate that a shell command is a `malariasim` invocation.

    Accepts:
      malariasim <args...>
      uv run malariasim <args...>
      uv run python -m mal_core.cli <args...>
      python -m mal_core.cli <args...>

    Rejects everything else, including any command that embeds shell
    metacharacters (would allow escaping the allowlist).
    """
    if not command or not isinstance(command, str):
        return False

    try:
        tokens = shlex.split(command)
    except ValueError:
        return False

    if not tokens:
        return False

    i = 0
    if tokens[0] == "uv":
        if len(tokens) < 2 or tokens[1] != "run":
            return False
        i = 2

    if tokens[i] == "malariasim":
        pass
    elif tokens[i] in ("python", "python3"):
        if len(tokens) < i + 3:
            return False
        if tokens[i + 1] != "-m" or tokens[i + 2] != "mal_core.cli":
            return False
    else:
        return False

    # Reject any token that could smuggle in extra shell behaviour.
    for tok in tokens:
        if any(c in tok for c in _BANNED_SHELL_CHARS):
            return False
    return True


class MalariasimShellBackend(LocalShellBackend):
    """Filesystem backend + shell restricted to the `malariasim` CLI.

    Inherits from `LocalShellBackend`, so the built-in `execute` tool is
    exposed to agents. `execute()` is overridden to only accept `malariasim`
    commands; filesystem policy hooks keep the old FilesystemPermission rules.
    """

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        if not _is_malariasim_command(command):
            return ExecuteResponse(
                output=(
                    "Error: Only `malariasim` commands are allowed via execute. "
                    f"Rejected: {command!r}"
                ),
                exit_code=1,
                truncated=False,
            )
        return super().execute(command, timeout=timeout)

    def read(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 2000,
    ) -> ReadResult:
        if _matches_any(file_path, _SECRET_READ_PATTERNS):
            return ReadResult(error=f"Read denied for protected path: {file_path}")
        return super().read(file_path, offset=offset, limit=limit)

    def write(self, file_path: str, content: str) -> WriteResult:
        if not self._write_allowed(file_path):
            return WriteResult(error=f"Write denied for path: {file_path}")
        return super().write(file_path, content)

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        if not self._write_allowed(file_path):
            return EditResult(error=f"Edit denied for path: {file_path}")
        return super().edit(file_path, old_string, new_string, replace_all)

    def _write_allowed(self, file_path: str) -> bool:
        if _matches_any(file_path, _WRITE_ALLOW_PATTERNS):
            return True
        if _matches_any(file_path, _WRITE_DENY_PATTERNS):
            return False
        return False


__all__ = ["MalariasimShellBackend", "_is_malariasim_command"]
