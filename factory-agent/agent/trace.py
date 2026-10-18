from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any


@dataclass(frozen=True)
class TraceEvent:
    stage: str
    status: str
    duration_ms: float
    details: dict[str, Any] = field(default_factory=dict)


class AgentTrace:
    """In-memory run trace used by the API, tests, and evaluation harness."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.metadata: dict[str, Any] = {}
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._started = perf_counter()
        self._stage_started: dict[str, float] = {}
        self._events: list[TraceEvent] = []

    def set_metadata(self, name: str, value: Any) -> None:
        self.metadata[name] = value

    def start(self, stage: str) -> None:
        self._stage_started[stage] = perf_counter()

    def end(
        self,
        stage: str,
        *,
        status: str = "ok",
        details: dict[str, Any] | None = None,
    ) -> None:
        started = self._stage_started.pop(stage, perf_counter())
        self._events.append(
            TraceEvent(
                stage=stage,
                status=status,
                duration_ms=round((perf_counter() - started) * 1000, 3),
                details=details or {},
            )
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "duration_ms": round((perf_counter() - self._started) * 1000, 3),
            "metadata": dict(self.metadata),
            "events": [asdict(event) for event in self._events],
        }
