from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class RunContext:
    """Trusted, server-created identity and capability context for one run."""

    task_id: str
    actor_id: str = "local-demo-user"
    tenant_id: str = "factory-demo"
    authorized_tools: frozenset[str] = field(default_factory=frozenset)
    reference_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
