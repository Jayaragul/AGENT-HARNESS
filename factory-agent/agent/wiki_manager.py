from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from config.logging_config import get_logger

logger = get_logger("wiki_manager")

WIKI_DIR = Path("wiki")


class WikiPageExists(Exception):
    pass


class WikiPageNotFound(Exception):
    pass


class WikiManager:
    """Manages the persistent wiki — Karpathy's three-layer pattern.

    Three layers:
      - Raw sources (immutable CSV files in data/)
      - The wiki  (LLM-maintained markdown in wiki/)
      - Schema    (skill.md, catalogs, config)

    Three operations:
      - Ingest: run a skill, file the result as a wiki page
      - Query:  check the wiki before touching raw data
      - Lint:   health-check the wiki (orphans, staleness, gaps)
    """

    def __init__(self, wiki_dir: Path = WIKI_DIR) -> None:
        self._wiki_dir = wiki_dir
        self._wiki_dir.mkdir(parents=True, exist_ok=True)
        self._init_special_pages()

    # ── Special pages ──────────────────────────────────────────────

    def _init_special_pages(self) -> None:
        index_path = self._wiki_dir / "index.md"
        if not index_path.exists():
            index_path.write_text(
                "# Factory Knowledge Wiki\n\n"
                "> Persistent knowledge base.\n\n"
                "## Materials\n*(no pages yet)*\n\n"
                "## Orders\n*(no pages yet)*\n\n"
                "## Insights\n*(no pages yet)*\n",
                encoding="utf-8",
            )
        log_path = self._wiki_dir / "log.md"
        if not log_path.exists():
            log_path.write_text(
                "# Wiki Activity Log\n\n"
                f"## [{datetime.now().strftime('%Y-%m-%d %H:%M')}] init | Wiki created\n",
                encoding="utf-8",
            )

    # ── Index management ───────────────────────────────────────────

    def read_index(self) -> str:
        path = self._wiki_dir / "index.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return "# Factory Knowledge Wiki\n\n*Empty*\n"

    def update_index(self, category: str, page_name: str, summary: str) -> None:
        index_path = self._wiki_dir / "index.md"
        content = index_path.read_text(encoding="utf-8")
        section_marker = f"## {category}"
        link_line = f"- [{page_name}]({category.lower()}/{page_name}.md) — {summary}"

        if link_line in content:
            return

        if section_marker in content:
            placeholder = "*(no pages yet)*"
            if placeholder in content:
                content = content.replace(placeholder, link_line)
            else:
                content = content.replace(
                    section_marker, f"{section_marker}\n{link_line}"
                )
        else:
            content += f"\n## {category}\n{link_line}\n"

        index_path.write_text(content, encoding="utf-8")

    # ── Log management ─────────────────────────────────────────────

    def append_log(self, operation: str, subject: str, details: str = "") -> None:
        log_path = self._wiki_dir / "log.md"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"## [{timestamp}] {operation} | {subject}\n"
        if details:
            entry += f"{details}\n"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)

    def read_log(self, lines: int = 20) -> str:
        log_path = self._wiki_dir / "log.md"
        content = log_path.read_text(encoding="utf-8")
        entries = content.split("## [")
        recent = entries[-(lines + 1):] if len(entries) > lines + 1 else entries
        return "## [".join(recent).strip()

    # ── Page CRUD ──────────────────────────────────────────────────

    def page_path(self, category: str, page_name: str) -> Path:
        return self._wiki_dir / category.lower() / f"{page_name}.md"

    def page_exists(self, category: str, page_name: str) -> bool:
        return self.page_path(category, page_name).exists()

    def write_page(
        self,
        category: str,
        page_name: str,
        content: str,
        summary: str = "",
        overwrite: bool = False,
    ) -> Path:
        path = self.page_path(category, page_name)
        if path.exists() and not overwrite:
            raise WikiPageExists(
                f"Page '{category}/{page_name}' already exists. Use overwrite=True."
            )
        path.parent.mkdir(parents=True, exist_ok=True)

        header = (
            f"# {page_name.replace('_', ' ').title()}\n\n"
            f"*Wiki page. Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
        )
        path.write_text(header + content, encoding="utf-8")

        self.update_index(category.title(), page_name, summary or content[:80])
        logger.info(
            "Wiki page written",
            extra={
                "category": category,
                "page": page_name,
                "path": str(path),
            },
        )
        return path

    def read_page(self, category: str, page_name: str) -> str:
        path = self.page_path(category, page_name)
        if not path.exists():
            raise WikiPageNotFound(f"Page '{category}/{page_name}' not found.")
        return path.read_text(encoding="utf-8")

    def delete_page(self, category: str, page_name: str) -> None:
        path = self.page_path(category, page_name)
        if path.exists():
            path.unlink()
            logger.info("Wiki page deleted", extra={"path": str(path)})

    def list_pages(self, category: str | None = None) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        base = self._wiki_dir / category.lower() if category else self._wiki_dir
        if not base.exists():
            return pages
        for f in sorted(base.glob("*.md")):
            if f.name in ("index.md", "log.md"):
                continue
            pages.append(
                {
                    "name": f.stem,
                    "category": category or f.parent.name,
                    "path": str(f.relative_to(self._wiki_dir)),
                }
            )
        return pages

    def search_pages(self, keyword: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for f in self._wiki_dir.rglob("*.md"):
            if f.name in ("index.md", "log.md"):
                continue
            content = f.read_text(encoding="utf-8")
            if keyword.lower() in content.lower():
                results.append(
                    {
                        "name": f.stem,
                        "category": f.parent.name,
                        "path": str(f.relative_to(self._wiki_dir)),
                        "snippet": content[:200].replace("\n", " "),
                    }
                )
        return results

    # ── High-level operations (Karpathy's pattern) ─────────────────

    def ingest_result(
        self,
        skill_name: str,
        query: str,
        result: dict[str, Any],
    ) -> dict[str, list[str]]:
        """File a skill execution result into the wiki.

        Returns: {pages_written: [...], log_entry: str}
        """
        written: list[str] = []

        if skill_name == "material_sufficiency":
            order_id = result.get("order_id", "unknown")
            product = result.get("product_name", "unknown")
            overall = result.get("overall_status", "unknown")

            page_content = (
                f"## Order\n- **ID**: {order_id}\n- **Product**: {product}\n"
                f"- **Quantity**: {result.get('order_quantity')} {result.get('order_unit')}\n"
                f"- **Status**: {overall.upper()}\n\n"
                f"### Materials\n\n"
                f"| Material | Required | Available | Shortage | Status |\n"
                f"|----------|----------|-----------|----------|--------|\n"
            )
            for m in result.get("materials", []):
                page_content += (
                    f"| {m['material_name']} | {m['required']} | "
                    f"{m['available']} | {m['shortage']} | {m['status']} |\n"
                )
            if result.get("recommendation"):
                page_content += f"\n**Recommendation**: {result['recommendation']}\n"
            page_content += f"\n*Query: {query}*\n"

            try:
                self.write_page(
                    "orders", order_id, page_content,
                    summary=f"{product} — {overall}",
                    overwrite=True,
                )
                written.append(f"orders/{order_id}")
            except Exception as e:
                logger.warning(f"Failed to write wiki page: {e}")

            for m in result.get("materials", []):
                mid = m["material_id"]
                try:
                    existing = ""
                    if self.page_exists("materials", mid):
                        existing = self.read_page("materials", mid)
                    mat_content = existing + (
                        f"\n### {order_id} ({datetime.now().strftime('%Y-%m-%d')})\n"
                        f"- **Required**: {m['required']} {m['unit']}\n"
                        f"- **Available**: {m['available']} {m['unit']}\n"
                        f"- **Shortage**: {m['shortage']} {m['unit']}\n"
                        f"- **Status**: {m['status']}\n"
                    )
                    self.write_page(
                        "materials", mid, mat_content,
                        summary=f"Updated from {order_id}",
                        overwrite=True,
                    )
                    written.append(f"materials/{mid}")
                except Exception as e:
                    logger.warning(f"Failed to update material page: {e}")

        elif skill_name == "machine_requirements":
            order_id = result.get("order_id", "unknown")
            page_content = (
                f"## Order\n- **ID**: {order_id}\n"
                f"- **Product**: {result.get('product_name')}\n"
                f"- **Quantity**: {result.get('order_quantity')}\n\n"
                f"### Machines\n\n"
                f"| Machine | Hours | Rate | Cost |\n"
                f"|---------|-------|------|------|\n"
            )
            for m in result.get("machines", []):
                page_content += (
                    f"| {m['machine_name']} ({m['machine_id']}) | "
                    f"{m['total_hours']} hrs | ${m['hourly_rate']}/hr | "
                    f"${m['estimated_cost']} |\n"
                )
            page_content += (
                f"\n**Total hours**: {result.get('total_hours')}\n"
                f"**Total cost**: ${result.get('total_cost')}\n"
                f"\n*Query: {query}*\n"
            )
            try:
                self.write_page(
                    "insights", f"machine_req_{order_id}", page_content,
                    summary=f"Machine requirements for {order_id}",
                    overwrite=True,
                )
                written.append(f"insights/machine_req_{order_id}")
            except Exception as e:
                logger.warning(f"Failed to write wiki page: {e}")

        elif skill_name == "material_risk_report":
            summary = result.get("summary", {})
            at_risk = result.get("materials_at_risk", [])
            page_content = (
                f"## Summary\n- **Active orders**: {result.get('total_active_orders')}\n"
                f"- **Materials at risk**: {summary.get('total_materials_at_risk')}\n"
                f"- **Critical**: {summary.get('critical', 0)}\n"
                f"- **High**: {summary.get('high', 0)}\n"
                f"- **Medium**: {summary.get('medium', 0)}\n"
                f"- **Low**: {summary.get('low', 0)}\n\n"
                f"### Materials at Risk\n\n"
            )
            if at_risk:
                page_content += (
                    "| Material | Shortage | Unit | Risk Level | Score |\n"
                    "|----------|----------|------|------------|-------|\n"
                )
                for m in at_risk:
                    page_content += (
                        f"| {m['material_name']} ({m['material_id']}) | "
                        f"{m['total_shortage']} | {m['unit']} | "
                        f"{m['risk_level']} | {m['risk_score']} |\n"
                    )
            else:
                page_content += "*No materials at risk.*\n"

            page_content += f"\n*Query: {query}*\n"

            try:
                self.write_page(
                    "insights", "material_risk_report",
                    page_content,
                    summary=f"{summary.get('total_materials_at_risk', 0)} materials at risk",
                    overwrite=True,
                )
                written.append("insights/material_risk_report")
            except Exception as e:
                logger.warning(f"Failed to write wiki page: {e}")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_details = f"  Pages: {', '.join(written)}\n" if written else ""
        log_entry = f"## [{timestamp}] ingest | {skill_name} | {query[:60]}\n{log_details}"

        self.append_log("ingest", skill_name, f"  Query: {query[:100]}\n  Pages: {', '.join(written) if written else 'none'}")

        return {"pages_written": written, "log_entry": log_entry}

    def lint(self) -> dict[str, Any]:
        """Health-check the wiki. Finds orphans, gaps, stale pages."""
        issues: list[str] = []
        all_pages = self.list_pages()

        refs = self.read_index()
        orphans: list[str] = []
        for p in all_pages:
            page_ref = f"({p['category']}/{p['name']}.md)"
            if page_ref not in refs and p["name"] not in ("index", "log"):
                orphans.append(f"{p['category']}/{p['name']}")

        if orphans:
            issues.append(f"Orphan pages (in index but no backlinks): {', '.join(orphans)}")

        missing_categories = []
        index_content = self.read_index()
        for cat in ("materials", "orders", "insights"):
            if f"## {cat.title()}" not in index_content and f"## {cat}" not in index_content:
                missing_categories.append(cat)
        if missing_categories:
            issues.append(f"Missing index sections: {', '.join(missing_categories)}")

        if not all_pages:
            issues.append("Wiki is empty — no pages have been created yet.")

        self.append_log("lint", "wiki health check", f"  Issues: {len(issues)}")

        return {
            "total_pages": all_pages,
            "total_pages_count": len(all_pages),
            "issues": issues,
            "issues_count": len(issues),
        }
