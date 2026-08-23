"""MalariasimShellBackend — LocalShellBackend with shell restricted to `malariasim`.

deepagents exposes a built-in `execute` tool whenever the agent's backend
implements `SandboxBackendProtocol`. We reuse that built-in tool (no custom
tool) and restrict what it can run via a backend policy hook:

- `execute()` only accepts `malariasim` invocations (optionally via
  `uv run ...` / `python -m mal_core.cli`). Anything else is rejected.
- `execute()` also accepts `malariasim build`, `malariasim test`, and
  `malariasim build-info` wrapper commands that translate to the real
  cmake/ctest invocations internally.
- `read()` / `write()` / `edit()` replicate the filesystem deny rules that
  used to be expressed as `FilesystemPermission` (secrets unreadable, writes
  confined to the gawt worktree).

This is the documented "backend policy hooks" approach:
https://docs.langchain.com/oss/python/deepagents/backends#add-policy-hooks
"""
from __future__ import annotations

import fnmatch
import os
import shlex
from pathlib import Path

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


# Subcommands that are wrappers for cmake/ctest build/test operations.
_BUILD_TEST_SUBCOMMANDS = frozenset({"build", "test", "build-info"})


def _is_build_test_command(command: str) -> bool:
    """Validate that a shell command is a ``malariasim build|test|build-info`` wrapper.

    These are safe wrapper subcommands that get translated to the real
    cmake/ctest invocations inside ``execute()``.  The raw ``cmake``,
    ``ctest``, ``pytest``, ``make`` commands remain blocked.

    Accepts:
      malariasim build [--target <name>]
      malariasim test [--test <name>]
      malariasim build-info
      uv run malariasim build

    Rejects:
      cmake --build .
      ctest --output-on-failure
      Everything that ``_is_malariasim_command`` rejects (shell metachars, etc.).
    """
    if not command or not isinstance(command, str):
        return False

    try:
        tokens = shlex.split(command)
    except ValueError:
        return False

    if not tokens:
        return False

    # Skip optional `uv run` prefix (same pattern as _is_malariasim_command).
    i = 0
    if tokens[0] == "uv":
        if len(tokens) < 2 or tokens[1] != "run":
            return False
        i = 2

    # Must start with `malariasim` followed by a build/test subcommand.
    if len(tokens) < i + 2:
        return False
    if tokens[i] != "malariasim":
        return False
    if tokens[i + 1] not in _BUILD_TEST_SUBCOMMANDS:
        return False

    # Reject any token that could smuggle in extra shell behaviour.
    for tok in tokens:
        if any(c in tok for c in _BANNED_SHELL_CHARS):
            return False
    return True


def _parse_build_test_tokens(command: str) -> tuple[str, dict[str, str]]:
    """Parse a ``malariasim build|test|build-info`` command.

    Returns:
        ``(subcommand, extras)`` where *extras* is a dict of parsed
        optional arguments (e.g. ``{"target": "abm"}`` or ``{"test": "TestFoo"}``).
    """
    tokens = shlex.split(command)

    i = 0
    if tokens[0] == "uv":
        i = 2

    subcmd = tokens[i + 1]
    extras: dict[str, str] = {}
    rest = tokens[i + 2:]

    # Parse ``--target <name>`` or ``--test <name>``
    j = 0
    while j < len(rest):
        if rest[j] == "--target" and j + 1 < len(rest):
            extras["target"] = rest[j + 1]
            j += 2
        elif rest[j] == "--test" and j + 1 < len(rest):
            extras["test"] = rest[j + 1]
            j += 2
        else:
            # Unknown flag — ignore gracefully (could be cmake passthrough).
            j += 1

    return subcmd, extras


def _tail_output(output: str, n: int = 30) -> str:
    """Return the last *n* lines of *output*, with a marker if truncated.

    This keeps agent context consumption bounded while still showing the
    most relevant results (success / failure summary at the end of cmake).
    """
    if not output:
        return ""

    lines = output.splitlines(keepends=True)
    if len(lines) <= n:
        return output

    prefix = f"… ({len(lines) - n} lines truncated)\n"
    return prefix + "".join(lines[-n:])


def _resolve_build_dir(root_dir: str | None = None) -> str:
    """Return the path to the CMake build directory inside the worktree.

    The ABM C++ engine lives in ``mal-core/`` and its build directory is
    ``mal-core/build/`` within the gawt worktree.

    If *root_dir* is ``None``, we fall back to looking for the worktree
    from the CWD (which deepagents sets to the repo root).
    """
    if root_dir is None:
        root_dir = os.getcwd()

    # Primary: gawt worktree layout.
    build_dir = Path(root_dir) / ".gitagent" / "worktree" / "mal-core" / "build"
    if build_dir.is_dir():
        return str(build_dir)

    # Fallback: repo-root/mal-core/build (monorepo layout without worktree).
    build_dir = Path(root_dir) / "mal-core" / "build"
    if build_dir.is_dir():
        return str(build_dir)

    # Last resort — return worktree path anyway (cmake will report a clear error).
    return str(Path(root_dir) / ".gitagent" / "worktree" / "mal-core" / "build")


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
        # --- Build / test wrapper subcommands ---
        if _is_build_test_command(command):
            return self._execute_build_test(command, timeout=timeout)

        # --- Standard malariasim CLI ---
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

    def _execute_build_test(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Translate a ``malariasim build|test|build-info`` wrapper to the
        real cmake/ctest command and execute it.

        The output is automatically tailed to 30 lines so the agent doesn't
        consume excessive context on large build logs.
        """
        subcmd, extras = _parse_build_test_tokens(command)
        build_dir = _resolve_build_dir()

        if subcmd == "build":
            target = extras.get("target")
            if target:
                real_cmd = f"cmake --build {build_dir} --target {target} -- -j$(nproc)"
            else:
                real_cmd = f"cmake --build {build_dir} -- -j$(nproc)"
        elif subcmd == "test":
            test_filter = extras.get("test")
            if test_filter:
                real_cmd = f"cd {build_dir} && ctest --output-on-failure -R {test_filter}"
            else:
                real_cmd = f"cd {build_dir} && ctest --output-on-failure"
        elif subcmd == "build-info":
            real_cmd = f"cd {build_dir} && cmake --build . --target help"
        else:
            return ExecuteResponse(
                output=f"Error: Unknown build/test subcommand: {subcmd!r}",
                exit_code=1,
                truncated=False,
            )

        resp = super().execute(real_cmd, timeout=timeout)
        # Tail the output so agents don't drown in build logs.
        resp = ExecuteResponse(
            output=_tail_output(resp.output),
            exit_code=resp.exit_code,
            truncated=resp.truncated,
        )
        return resp

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


__all__ = [
    "MalariasimShellBackend",
    "_is_malariasim_command",
    "_is_build_test_command",
    "_tail_output",
    "_parse_build_test_tokens",
    "_resolve_build_dir",
]
