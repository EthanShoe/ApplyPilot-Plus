"""In-memory pipeline state — tracks whether a stage is currently running."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class StageRun:
    stage: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str = "running"  # running | done | error | stopped
    error: Optional[str] = None


class PipelineState:
    """Thread-safe singleton tracking pipeline execution."""

    def __init__(self):
        self._lock = threading.Lock()
        self._current: Optional[StageRun] = None
        self._stop_requested: bool = False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._current is not None and self._current.status == "running"

    def start(self, stage: str) -> bool:
        """Attempt to start a stage. Returns False if already running."""
        with self._lock:
            if self._current is not None and self._current.status == "running":
                return False
            self._current = StageRun(stage=stage, started_at=datetime.now())
            self._stop_requested = False
            return True

    def request_stop(self) -> None:
        with self._lock:
            self._stop_requested = True

    def should_stop(self) -> bool:
        with self._lock:
            return self._stop_requested

    def finish(self, status: str = "done", error: Optional[str] = None) -> None:
        with self._lock:
            if self._current:
                self._current.finished_at = datetime.now()
                self._current.status = status
                self._current.error = error

    def as_dict(self) -> dict:
        with self._lock:
            if not self._current:
                return {"is_running": False, "stage": None, "started_at": None,
                        "status": "idle", "error": None, "elapsed_seconds": None}
            run = self._current
            elapsed = None
            if run.started_at:
                end = run.finished_at or datetime.now()
                elapsed = round((end - run.started_at).total_seconds())
            return {
                "is_running": run.status == "running",
                "stage": run.stage,
                "started_at": run.started_at.strftime("%H:%M:%S") if run.started_at else None,
                "status": run.status,
                "error": run.error,
                "elapsed_seconds": elapsed,
            }


pipeline_state = PipelineState()
