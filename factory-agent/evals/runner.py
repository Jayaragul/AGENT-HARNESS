from __future__ import annotations

import argparse
import json
import math
import statistics
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from agent.harness import AgentHarness
from config.settings import APP_ROOT, BackendType, Settings


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    expected: Any
    actual: Any


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    category: str
    score: float
    passed: bool
    latency_ms: float
    checks: list[CheckResult]
    response: dict[str, Any]


def _value_at_path(payload: Any, path: str) -> Any:
    current = payload
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(path)
    return current


def _evaluate_assertion(response: dict[str, Any], spec: dict[str, Any]) -> CheckResult:
    path = spec["path"]
    operator = spec.get("operator", "equals")
    expected = spec.get("value")
    try:
        actual = _value_at_path(response, path)
        if operator == "equals":
            passed = actual == expected
        elif operator == "contains":
            passed = expected in actual
        elif operator == "contains_all":
            passed = all(item in actual for item in expected)
        elif operator == "greater_than":
            passed = actual > expected
        elif operator == "less_than":
            passed = actual < expected
        elif operator == "truthy":
            passed = bool(actual)
        elif operator == "exists":
            passed = True
        else:
            raise ValueError(f"Unknown assertion operator: {operator}")
    except (IndexError, KeyError, TypeError, ValueError):
        actual = "<missing>"
        passed = False
    return CheckResult(
        name=f"{path} {operator}",
        passed=passed,
        expected=expected,
        actual=actual,
    )


class EvaluationRunner:
    """Runs behavioral cases and produces machine- and human-readable reports."""

    def __init__(
        self,
        cases_path: Path,
        *,
        backend: BackendType = BackendType.MOCK,
        min_score: float = 0.95,
        min_pass_rate: float = 0.90,
    ) -> None:
        self.cases_path = cases_path
        self.backend = backend
        self.min_score = min_score
        self.min_pass_rate = min_pass_rate

    def load_cases(self) -> list[dict[str, Any]]:
        cases: list[dict[str, Any]] = []
        for line_number, line in enumerate(
            self.cases_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL at {self.cases_path}:{line_number}: {exc}"
                ) from exc
            for required in ("id", "category", "turns"):
                if required not in case:
                    raise ValueError(
                        f"Case at line {line_number} is missing '{required}'."
                    )
            cases.append(case)
        if not cases:
            raise ValueError(f"No evaluation cases found in {self.cases_path}")
        return cases

    def run(self) -> dict[str, Any]:
        started = perf_counter()
        case_results: list[CaseResult] = []

        with tempfile.TemporaryDirectory(prefix="factory-agent-eval-") as temp_dir:
            temp = Path(temp_dir)
            settings = Settings(
                backend=self.backend,
                wiki_path=temp / "wiki",
                log_path=temp / "logs",
                output_path=temp / "outputs",
            )
            harness = AgentHarness(settings)
            try:
                for case in self.load_cases():
                    case_results.append(self._run_case(harness, case))
            finally:
                harness.close()

        scores = [item.score for item in case_results]
        latencies = [item.latency_ms for item in case_results]
        passed_count = sum(item.passed for item in case_results)
        overall_score = statistics.fmean(scores)
        pass_rate = passed_count / len(case_results)

        categories: dict[str, dict[str, Any]] = {}
        for category in sorted({item.category for item in case_results}):
            group = [item for item in case_results if item.category == category]
            categories[category] = {
                "cases": len(group),
                "passed": sum(item.passed for item in group),
                "score": round(statistics.fmean(item.score for item in group), 4),
            }

        report = {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "backend": self.backend.value,
            "cases_file": str(self.cases_path),
            "summary": {
                "total_cases": len(case_results),
                "passed_cases": passed_count,
                "failed_cases": len(case_results) - passed_count,
                "pass_rate": round(pass_rate, 4),
                "overall_score": round(overall_score, 4),
                "p50_latency_ms": round(statistics.median(latencies), 3),
                "p95_latency_ms": round(self._percentile(latencies, 0.95), 3),
                "duration_ms": round((perf_counter() - started) * 1000, 3),
            },
            "thresholds": {
                "min_score": self.min_score,
                "min_pass_rate": self.min_pass_rate,
            },
            "categories": categories,
            "passed": overall_score >= self.min_score and pass_rate >= self.min_pass_rate,
            "cases": [asdict(item) for item in case_results],
        }
        return report

    def _run_case(
        self, harness: AgentHarness, case: dict[str, Any]
    ) -> CaseResult:
        response: dict[str, Any] = {}
        session_id: str | None = None
        started = perf_counter()
        for query in case["turns"]:
            response = harness.process_query(query, session_id=session_id)
            session_id = response.get("session_id")
        latency_ms = (perf_counter() - started) * 1000

        checks: list[CheckResult] = []
        if "expected_skill" in case:
            checks.append(
                CheckResult(
                    name="skill",
                    passed=response.get("skill_name") == case["expected_skill"],
                    expected=case["expected_skill"],
                    actual=response.get("skill_name"),
                )
            )
        if "expected_decision" in case:
            actual = (response.get("result") or {}).get("decision")
            checks.append(
                CheckResult(
                    name="decision",
                    passed=actual == case["expected_decision"],
                    expected=case["expected_decision"],
                    actual=actual,
                )
            )
        if "expected_tools" in case:
            actual = (response.get("result") or {}).get("tools_used", [])
            checks.append(
                CheckResult(
                    name="tool_selection",
                    passed=actual == case["expected_tools"],
                    expected=case["expected_tools"],
                    actual=actual,
                )
            )
        checks.extend(
            _evaluate_assertion(response, spec)
            for spec in case.get("assertions", [])
        )

        score = statistics.fmean(check.passed for check in checks) if checks else 0.0
        return CaseResult(
            case_id=case["id"],
            category=case["category"],
            score=round(score, 4),
            passed=all(check.passed for check in checks),
            latency_ms=round(latency_ms, 3),
            checks=checks,
            response=response,
        )

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        ordered = sorted(values)
        rank = max(0, math.ceil(percentile * len(ordered)) - 1)
        return ordered[rank]

    @staticmethod
    def markdown(report: dict[str, Any]) -> str:
        summary = report["summary"]
        lines = [
            "# Factory Agent Evaluation Report",
            "",
            f"**Status:** {'PASS' if report['passed'] else 'FAIL'}",
            f"**Overall score:** {summary['overall_score']:.1%}",
            f"**Pass rate:** {summary['pass_rate']:.1%} "
            f"({summary['passed_cases']}/{summary['total_cases']})",
            f"**Latency:** p50 {summary['p50_latency_ms']} ms, "
            f"p95 {summary['p95_latency_ms']} ms",
            "",
            "## Category scores",
            "",
            "| Category | Passed | Cases | Score |",
            "|---|---:|---:|---:|",
        ]
        for name, result in report["categories"].items():
            lines.append(
                f"| {name} | {result['passed']} | {result['cases']} | "
                f"{result['score']:.1%} |"
            )
        lines.extend(
            [
                "",
                "## Cases",
                "",
                "| Case | Category | Result | Score | Latency |",
                "|---|---|---|---:|---:|",
            ]
        )
        for case in report["cases"]:
            lines.append(
                f"| {case['case_id']} | {case['category']} | "
                f"{'PASS' if case['passed'] else 'FAIL'} | "
                f"{case['score']:.1%} | {case['latency_ms']} ms |"
            )
            for check in case["checks"]:
                if not check["passed"]:
                    lines.append(
                        f"| ↳ {check['name']} | expected `{check['expected']}` | "
                        f"actual `{check['actual']}` |  |  |"
                    )
        return "\n".join(lines) + "\n"

    @staticmethod
    def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "latest.json"
        markdown_path = output_dir / "latest.md"
        json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        markdown_path.write_text(EvaluationRunner.markdown(report), encoding="utf-8")
        return json_path, markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Factory Agent behavioral evals.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=APP_ROOT / "evals" / "cases" / "core.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=APP_ROOT / "eval_reports",
    )
    parser.add_argument(
        "--backend",
        choices=[backend.value for backend in BackendType],
        default=BackendType.MOCK.value,
        help="MOCK is deterministic/offline; other backends run model evals (OLLAMA requires a local server).",
    )
    parser.add_argument("--min-score", type=float, default=0.95)
    parser.add_argument("--min-pass-rate", type=float, default=0.90)
    args = parser.parse_args()

    runner = EvaluationRunner(
        args.cases,
        backend=BackendType(args.backend),
        min_score=args.min_score,
        min_pass_rate=args.min_pass_rate,
    )
    report = runner.run()
    json_path, markdown_path = runner.write_report(report, args.output)
    print(runner.markdown(report))
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
