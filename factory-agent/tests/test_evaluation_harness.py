from __future__ import annotations

import json
from pathlib import Path

from config.settings import APP_ROOT
from evals.runner import EvaluationRunner


def test_core_evaluation_suite_meets_quality_gate(tmp_path: Path) -> None:
    runner = EvaluationRunner(
        APP_ROOT / "evals" / "cases" / "core.jsonl",
        min_score=0.95,
        min_pass_rate=0.90,
    )

    report = runner.run()

    assert report["passed"] is True
    assert report["summary"]["total_cases"] >= 10
    assert report["summary"]["overall_score"] >= 0.95
    assert set(report["categories"]) >= {
        "task_success",
        "routing",
        "orchestration",
        "robustness",
        "safety",
    }

    json_path, markdown_path = runner.write_report(report, tmp_path)
    persisted = json.loads(json_path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == "1.0"
    assert "Factory Agent Evaluation Report" in markdown_path.read_text(
        encoding="utf-8"
    )
