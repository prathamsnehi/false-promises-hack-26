"""Audit log: one JSON line per decision. Done for you; extend the fields if your policy needs more."""
import json
import os
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

# gate.py judge/try set GATE_LOG_DIR so evaluation runs never pollute your demo audit sample.
LOG = Path(os.getenv("GATE_LOG_DIR") or Path(__file__).parent) / "audit_log.jsonl"
_lock = threading.Lock()
MAX_LINE_BYTES = 2_000_000
MAX_TAIL_BYTES = 32_000_000


class ReviewError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _records(path, recent=False):
    """Read bounded lines, ignoring incomplete/corrupt entries after an interrupted write."""
    if not path.is_file():
        return
    with path.open("rb") as handle:
        if recent:
            size = handle.seek(0, 2)
            offset = max(0, size - MAX_TAIL_BYTES)
            handle.seek(offset)
            if offset:
                handle.readline(MAX_LINE_BYTES + 1)
        while True:
            line = handle.readline(MAX_LINE_BYTES + 1)
            if not line:
                break
            if len(line) > MAX_LINE_BYTES:
                while line and not line.endswith(b"\n"):
                    line = handle.readline(MAX_LINE_BYTES + 1)
                continue
            if not line.endswith(b"\n"):
                continue
            try:
                entry = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(entry, dict):
                yield entry


def latest(limit=30):
    with _lock:
        entries = list(deque(_records(LOG, recent=True), maxlen=limit))
        by_id = {entry.get("decision_id"): entry for entry in entries if entry.get("decision_id")}
        for entry in entries:
            entry["reviews"] = []
        for review in _records(LOG.parent / "reviews.jsonl", recent=True):
            target = by_id.get(review.get("decision_id"))
            if target is not None:
                target["reviews"].append(review)
        return list(reversed(entries))


def review(decision_id, disposition, note):
    if (not isinstance(decision_id, str) or not decision_id.strip() or len(decision_id) > 100
            or disposition not in ("reject", "request_revision")
            or not isinstance(note, str) or not note.strip() or len(note) > 1000):
        raise ReviewError(400, "Supply decision_id, reject/request_revision, and a note of 1 to 1000 characters")
    with _lock:
        decision = next((entry for entry in _records(LOG) if entry.get("decision_id") == decision_id), None)
        if decision is None:
            raise ReviewError(404, "Decision not found in this audit log")
        if decision.get("decision") != "HOLD_FOR_REVIEW":
            raise ReviewError(409, "Only held decisions can receive a review disposition")
        event = {"review_id": str(uuid.uuid4()), "decision_id": decision_id,
                 "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "disposition": disposition, "note": note.strip()}
        with (LOG.parent / "reviews.jsonl").open("a") as handle:
            handle.write(json.dumps(event) + "\n")
        return event


def record(persona, text, context, decision):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "persona": persona,
        "input": text,
        "context": context,
        "decision": decision.decision,
        "reason": decision.reason,
        "evidence": decision.evidence,
        "ezio": decision.ezio,
        "decision_id": getattr(decision, "decision_id", None),
        "checks": getattr(decision, "checks", []),
        "counterexamples": getattr(decision, "counterexamples", []),
    }
    with _lock, LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")
