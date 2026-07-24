"""CppAbmWrapper — thin Python wrapper around the compiled C++ ABM binary."""
from __future__ import annotations
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

class CppAbmWrapper:
    def __init__(self, binary_path: Path | None = None):
        self.binary = binary_path or self._resolve_binary()
        self._flags_schema: dict[str, dict[str, Any]] | None = None

    def _resolve_binary(self) -> Path:
        pkg_dir = Path(__file__).parent
        bin_path = pkg_dir / "bin" / f"mal_abm_fast_{sys.platform}"
        if bin_path.exists():
            return bin_path
        build_path = pkg_dir / "build" / "src" / "mal_abm_fast"
        if build_path.exists():
            return build_path
        raise FileNotFoundError(f"ABM binary not found. Run: bash {pkg_dir / 'build.sh'}")

    def _introspect_flags(self) -> dict[str, dict[str, Any]]:
        try:
            result = subprocess.run([str(self.binary), "--help"], capture_output=True, text=True, timeout=10)
            output = result.stdout + result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {}
        flags: dict[str, dict[str, Any]] = {}
        for match in re.finditer(r"--([\w-]+)\s+(?:<(\w+)>)?\s*(.*)", output):
            name = match.group(1).replace("-", "_")
            ftype = match.group(2) or "bool"
            desc = match.group(3).strip()
            tmap = {"int": int, "float": float, "str": str, "string": str, "bool": bool}
            flags[name] = {"type": tmap.get(ftype, str), "default": None, "help": desc}
        return flags

    def run(self, **flags) -> dict[str, Any]:
        if self._flags_schema is None:
            self._flags_schema = self._introspect_flags()
        cmd = [str(self.binary)]
        for name, value in flags.items():
            if value is None:
                continue
            cli = f"--{name.replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    cmd.append(cli)
            else:
                cmd.extend([cli, str(value)])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}

    def get_flags_schema(self) -> dict[str, dict[str, Any]]:
        if self._flags_schema is None:
            self._flags_schema = self._introspect_flags()
        return self._flags_schema
