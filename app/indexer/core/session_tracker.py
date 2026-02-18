"""
Processing session tracker for the Policy Indexer pipeline.

Tracks the status, timing, and errors of each document processing run.
Provides the ``/api/processing_status`` endpoint with rich observability
data per session.

Storage is in-memory (with TTL cleanup) by default. Can be extended to
persist to Cosmos DB or blob storage for durability.
"""

import logging
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("policy-indexer")


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProcessingStep:
    """A single step within a processing session."""

    name: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    detail: Optional[str] = None


@dataclass
class ProcessingSession:
    """
    Tracks the lifecycle of a single document processing run.

    Created when a blob event is received; updated as each step
    (download, OCR, chunking, embedding, indexing) completes.
    """

    session_id: str
    blob_name: str
    status: str = "running"  # running, completed, failed
    created_at: str = ""
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    success: Optional[bool] = None
    detail: Optional[str] = None
    steps: Dict[str, ProcessingStep] = field(default_factory=dict)

    _start_time: float = field(default=0.0, repr=False)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self._start_time:
            self._start_time = time.time()

        # Pre-create standard steps
        for step_name in ("download", "ocr", "chunking", "embedding", "indexing"):
            if step_name not in self.steps:
                self.steps[step_name] = ProcessingStep(name=step_name)

    def update_step(
        self, step_name: str, status: StepStatus, detail: Optional[str] = None
    ) -> None:
        """Update a processing step's status and timing."""
        step = self.steps.get(step_name)
        if not step:
            step = ProcessingStep(name=step_name)
            self.steps[step_name] = step

        now = datetime.now(timezone.utc).isoformat()

        if status == StepStatus.RUNNING:
            step.status = StepStatus.RUNNING
            step.started_at = now
        elif status in (StepStatus.COMPLETED, StepStatus.FAILED):
            step.status = status
            step.completed_at = now
            if step.started_at:
                try:
                    start = datetime.fromisoformat(step.started_at)
                    end = datetime.fromisoformat(now)
                    step.duration_seconds = (end - start).total_seconds()
                except (ValueError, TypeError):
                    pass

        if detail:
            step.detail = detail

    def complete(self, success: bool, detail: Optional[str] = None) -> None:
        """Mark the session as complete."""
        self.status = "completed" if success else "failed"
        self.success = success
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.duration_seconds = time.time() - self._start_time
        self.detail = detail

        # Mark any still-pending steps as skipped, any running as failed
        for step in self.steps.values():
            if step.status == StepStatus.PENDING:
                step.status = StepStatus.SKIPPED
            elif step.status == StepStatus.RUNNING and not success:
                step.status = StepStatus.FAILED
                step.detail = detail

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-friendly dict."""
        return {
            "session_id": self.session_id,
            "blob_name": self.blob_name,
            "status": self.status,
            "success": self.success,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "detail": self.detail,
            "steps": {
                name: {
                    "status": step.status.value,
                    "started_at": step.started_at,
                    "completed_at": step.completed_at,
                    "duration_seconds": step.duration_seconds,
                    "detail": step.detail,
                }
                for name, step in self.steps.items()
            },
        }


class SessionTracker:
    """
    In-memory session store with TTL-based cleanup.

    Thread-safe. Stores the most recent ``max_sessions`` sessions
    and evicts entries older than ``ttl_seconds``.
    """

    def __init__(
        self,
        max_sessions: int = 1000,
        ttl_seconds: int = 3600 * 24,  # 24 hours
    ):
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self._sessions: OrderedDict[str, ProcessingSession] = OrderedDict()
        self._lock = threading.Lock()

    def create_session(self, blob_name: str) -> ProcessingSession:
        """Create and register a new processing session."""
        session_id = str(uuid.uuid4())[:8]  # short, human-friendly
        session = ProcessingSession(session_id=session_id, blob_name=blob_name)

        with self._lock:
            self._sessions[session_id] = session
            self._evict_old()

        logger.info("Created session %s for %s", session_id, blob_name)
        return session

    def get_session(self, session_id: str) -> Optional[ProcessingSession]:
        """Retrieve a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def get_sessions_by_blob(self, blob_name: str) -> List[ProcessingSession]:
        """Retrieve all sessions for a given blob name."""
        with self._lock:
            return [
                s for s in self._sessions.values() if s.blob_name == blob_name
            ]

    def list_recent(self, limit: int = 50) -> List[ProcessingSession]:
        """List the most recent sessions."""
        with self._lock:
            sessions = list(self._sessions.values())
        return sessions[-limit:]

    def list_failed(self, limit: int = 50) -> List[ProcessingSession]:
        """List the most recent failed sessions."""
        with self._lock:
            failed = [
                s for s in self._sessions.values() if s.status == "failed"
            ]
        return failed[-limit:]

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of all tracked sessions."""
        with self._lock:
            sessions = list(self._sessions.values())

        total = len(sessions)
        running = sum(1 for s in sessions if s.status == "running")
        completed = sum(1 for s in sessions if s.status == "completed" and s.success)
        failed = sum(1 for s in sessions if s.status == "failed")

        return {
            "total_sessions": total,
            "running": running,
            "completed": completed,
            "failed": failed,
            "recent_failures": [
                s.to_dict() for s in sessions if s.status == "failed"
            ][-5:],
        }

    def _evict_old(self) -> None:
        """Remove sessions exceeding max count or TTL."""
        # Evict by count
        while len(self._sessions) > self.max_sessions:
            self._sessions.popitem(last=False)

        # Evict by TTL
        cutoff = time.time() - self.ttl_seconds
        to_remove = []
        for sid, session in self._sessions.items():
            if session._start_time < cutoff:
                to_remove.append(sid)
            else:
                break  # OrderedDict is insertion-ordered

        for sid in to_remove:
            del self._sessions[sid]


# -- Singleton tracker instance ---
# Shared across all function invocations within the same process
_global_tracker: Optional[SessionTracker] = None
_tracker_lock = threading.Lock()


def get_global_tracker() -> SessionTracker:
    """Get the global session tracker singleton."""
    global _global_tracker
    if _global_tracker is None:
        with _tracker_lock:
            if _global_tracker is None:
                _global_tracker = SessionTracker()
    return _global_tracker
