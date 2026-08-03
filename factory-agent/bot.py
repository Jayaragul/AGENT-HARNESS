from __future__ import annotations

from agent.harness import AgentHarness
from config.logging_config import get_logger
from config.settings import Settings

logger = get_logger("bot")


def print_separator() -> None:
    print("-" * 60)


def format_response(response: dict) -> None:
    print_separator()

    if response.get("error"):
        if response.get("explanation"):
            print(response["explanation"])
        else:
            print(f"Error: {response['error']}")
        return

    skill_name = response.get("skill_name", "unknown")
    non_action_skills = (
        "chat", "help", "knowledge", "answer_from_context",
        "clarification_required", "unsupported", "security_rejected",
        "tool_calls",
    )
    wiki_skills = ("wiki_index", "wiki_log", "wiki_search", "wiki_list", "wiki_help", "wiki_lint")

    if skill_name == "wiki_lint":
        result = response.get("result", {})
        print("=== Wiki Health Check ===")
        print(f"Total pages: {result.get('total_pages_count', 0)}")
        issues = result.get("issues", [])
        if issues:
            print(f"Issues found: {result.get('issues_count', 0)}")
            for issue in issues:
                print(f"  ! {issue}")
        else:
            print("No issues — wiki is healthy.")
        return

    if skill_name in wiki_skills:
        result = response.get("result", {})
        print(result.get("message", ""))
        return

    if skill_name not in non_action_skills:
        print(f"Selected skill: {skill_name}")

    datasets = response.get("datasets_used", [])
    if datasets:
        print(f"Datasets used: {', '.join(datasets)}")

    wiki_pages = response.get("wiki_pages_consulted", [])
    if wiki_pages:
        print(f"Wiki pages consulted: {', '.join(wiki_pages)}")

    result = response.get("result", {})
    if result:
        if skill_name in non_action_skills:
            if response.get("explanation"):
                print(response["explanation"])
            else:
                print(result.get("message", "Information unavailable."))

            available_datasets = result.get("available_datasets", [])
            if available_datasets:
                print(f"Available datasets: {', '.join(available_datasets)}")

            available_skills = result.get("available_skills", [])
            if available_skills:
                print(f"Available skills: {', '.join(available_skills)}")

            examples = result.get("example_questions", [])
            if examples:
                print("Example questions:")
                for example in examples:
                    print(f"  - {example}")

        if skill_name == "material_sufficiency":
            print(f"Order: {result.get('order_id', 'N/A')}")
            print(f"Product: {result.get('product_name', 'N/A')}")
            print(f"Quantity: {result.get('order_quantity', 'N/A')} {result.get('order_unit', '')}")
            print(f"Status: {result.get('overall_status', 'N/A').upper()}")
            for mat in result.get("materials", []):
                status = mat.get("status", "")
                if status == "insufficient":
                    print(
                        f"  Material {mat.get('material_name', '')}: "
                        f"need {mat.get('required', 0)} {mat.get('unit', '')}, "
                        f"have {mat.get('available', 0)} {mat.get('unit', '')}, "
                        f"shortage {mat.get('shortage', 0)} {mat.get('unit', '')}"
                    )
                else:
                    print(
                        f"  Material {mat.get('material_name', '')}: "
                        f"need {mat.get('required', 0)} {mat.get('unit', '')}, "
                        f"have {mat.get('available', 0)} {mat.get('unit', '')}, "
                        f"sufficient"
                    )
            if result.get("recommendation"):
                print(f"\nRecommendation: {result['recommendation']}")

        elif skill_name == "machine_requirements":
            print(f"Order: {result.get('order_id', 'N/A')}")
            print(f"Product: {result.get('product_name', 'N/A')}")
            print(f"Quantity: {result.get('order_quantity', 'N/A')}")
            for mc in result.get("machines", []):
                print(
                    f"  Machine: {mc.get('machine_name', '')} ({mc.get('machine_id', '')}) "
                    f"- {mc.get('total_hours', 0)} hrs @ ${mc.get('hourly_rate', 0)}/hr "
                    f"= ${mc.get('estimated_cost', 0)}"
                )
            print(f"\nTotal machine time: {result.get('total_hours', 0)} hours")
            print(f"Total estimated cost: ${result.get('total_cost', 0)}")

        elif skill_name == "material_risk_report":
            print(f"Total active orders: {result.get('total_active_orders', 0)}")
            summary = result.get("summary", {})
            print(
                f"Materials at risk: {summary.get('total_materials_at_risk', 0)} "
                f"(critical: {summary.get('critical', 0)}, "
                f"high: {summary.get('high', 0)}, "
                f"medium: {summary.get('medium', 0)}, "
                f"low: {summary.get('low', 0)})"
            )
            for mat in result.get("materials_at_risk", []):
                print(
                    f"  {mat.get('material_name', '')}: "
                    f"shortage {mat.get('total_shortage', 0)} {mat.get('unit', '')}, "
                    f"{mat.get('risk_level', '')} risk (score {mat.get('risk_score', 0)})"
                )

        if skill_name not in non_action_skills:
            print(f"\nData last updated: {result.get('data_last_updated', 'N/A')}")

    warnings = response.get("warnings")
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")

    if response.get("report_path"):
        print(f"\nReport saved: {response['report_path']}")

    print_separator()


def main() -> None:
    settings = Settings()
    harness = AgentHarness(settings)

    print("Factory AI Agent Harness")
    print("Type 'exit' or 'quit' to stop.")
    print("Commands: 'lint' (wiki health), 'wiki index' (browse), 'wiki log' (history)")
    print_separator()

    while True:
        try:
            query = input("\nUser: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if query.lower() in ("exit", "quit", "bye"):
            print("Goodbye.")
            break

        if not query:
            continue

        try:
            response = harness.process_query(query)
            format_response(response)
        except Exception as e:
            print(f"\nSystem error: {e}")


if __name__ == "__main__":
    main()
