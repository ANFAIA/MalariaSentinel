"""Configuration of the paper-corpus tool, read from ``mal-core/config/papers.yaml``.

The file holds the output root, the contact e-mail sent to Unpaywall and
Crossref, and the docling device. It holds no credentials. The e-mail is never
hard-coded in Python: the placeholder value disables the Unpaywall step.

Each person sets their own e-mail in the environment variable
``MALARIASIM_PAPERS_EMAIL``; it overrides the file, so the address never enters
the repository.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

MAL_CORE_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = MAL_CORE_DIR.parent
DEFAULT_CONFIG = MAL_CORE_DIR / "config" / "papers.yaml"

DEVICES = ("cpu", "mps")
PLACEHOLDER_EMAIL = "REPLACE-ME@example.invalid"
EMAIL_ENV_VAR = "MALARIASIM_PAPERS_EMAIL"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RESERVED_DOMAINS = (".invalid", ".example", ".test", "example.com", "example.org", "example.net")


@dataclass(frozen=True)
class PapersConfig:
    """Corpus settings: output root, contact e-mail and docling device."""
    output_root: str
    unpaywall_email: str
    device: str

    def papers_root(self, repo_root: Path = REPO_ROOT) -> Path:
        """Absolute corpus root. An absolute ``output_root`` is used as given."""
        root = Path(self.output_root)
        return root if root.is_absolute() else repo_root / root


def email_is_usable(email: str | None) -> bool:
    """True for a syntactically valid address outside reserved/placeholder domains."""
    if not email or not _EMAIL_RE.match(email.strip()):
        return False
    domain = email.strip().rsplit("@", 1)[1].lower()
    return not any(domain == d.lstrip(".") or domain.endswith(d) for d in _RESERVED_DOMAINS)


def load_config(path: Path = DEFAULT_CONFIG, *, environ: Mapping[str, str] | None = None) -> PapersConfig:
    """Load and validate ``papers.yaml``. Raises ``ValueError`` on a bad file.

    ``MALARIASIM_PAPERS_EMAIL`` in the environment, when set and non-empty,
    replaces ``unpaywall_email`` from the file.
    """
    if not path.is_file():
        raise ValueError(f"papers config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    required = ("output_root", "unpaywall_email", "device")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"{path}: missing keys {missing}")
    device = str(data["device"])
    if device not in DEVICES:
        raise ValueError(f"{path}: device must be one of {DEVICES}, got {device!r}")
    env = os.environ if environ is None else environ
    email = (env.get(EMAIL_ENV_VAR) or "").strip() or str(data["unpaywall_email"])
    return PapersConfig(
        output_root=str(data["output_root"]),
        unpaywall_email=email,
        device=device,
    )
