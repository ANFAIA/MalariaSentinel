"""Inter-agent mailbox — file-based message passing."""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

def _session_dir() -> Path:
    """Return the active session's mailbox root. Creates dirs if needed."""
    # Session dir is set by the orchestrator via set_session_dir()
    if _SESSION_DIR is not None:
        d = _SESSION_DIR / "mailbox"
        d.mkdir(parents=True, exist_ok=True)
        return d
    # Fallback: use runs/mailbox/
    d = Path("runs/mailbox")
    d.mkdir(parents=True, exist_ok=True)
    return d

_SESSION_DIR: Path | None = None

def set_session_dir(path: Path) -> None:
    global _SESSION_DIR
    _SESSION_DIR = path

def mailbox_send(
    to: str,
    re: str,
    summary: str,
    from_: str = "orchestrator",
    severity: str = "non-breaking",
    spec_target: str = "",
    ask: str = "ack",
    thread_id: str = "",
    ttl_minutes: int = 60,
) -> str:
    """Send a message to a subagent's inbox."""
    msg = {
        "id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        "from": from_,
        "to": to,
        "re": re,
        "severity": severity,
        "spec_target": spec_target or to,
        "summary": summary,
        "ask": ask,
        "thread_id": thread_id,
        "ttl_minutes": ttl_minutes,
        "status": "open",
    }
    inbox = _session_dir() / f"inbox-{to}"
    inbox.mkdir(parents=True, exist_ok=True)
    msg_file = inbox / f"{msg['id']}.json"
    msg_file.write_text(json.dumps(msg, indent=2))
    return json.dumps({"status": "sent", "message_id": msg["id"], "to": to})

def mailbox_check_inbox(subagent: str) -> str:
    """Check inbox for a subagent. Returns list of open messages."""
    inbox = _session_dir() / f"inbox-{subagent}"
    if not inbox.exists():
        return json.dumps({"messages": [], "count": 0})
    messages = []
    for f in sorted(inbox.glob("*.json")):
        try:
            msg = json.loads(f.read_text())
            if msg.get("status") == "open":
                messages.append(msg)
        except (json.JSONDecodeError, OSError):
            continue
    return json.dumps({"messages": messages, "count": len(messages)})

def mailbox_mark_resolved(message_id: str, subagent: str, resolution: str = "ack") -> str:
    """Mark a message as resolved."""
    inbox = _session_dir() / f"inbox-{subagent}"
    msg_file = inbox / f"{message_id}.json"
    if not msg_file.exists():
        return json.dumps({"error": f"Message {message_id} not found", "status": "not_found"})
    msg = json.loads(msg_file.read_text())
    msg["status"] = "resolved"
    msg["resolution"] = resolution
    msg["resolved_ts"] = datetime.now(timezone.utc).isoformat()
    msg_file.write_text(json.dumps(msg, indent=2))
    # Move to archive
    archive = _session_dir() / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    msg_file.rename(archive / f"{message_id}.json")
    return json.dumps({"status": "resolved", "message_id": message_id})
