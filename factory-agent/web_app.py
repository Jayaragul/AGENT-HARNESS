from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.harness import AgentHarness
from config.settings import Settings

harness: AgentHarness | None = None


def initialize_harness() -> None:
    global harness
    harness = AgentHarness(Settings())


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_harness()
    try:
        yield
    finally:
        if harness is not None:
            harness.close()


app = FastAPI(title="Factory Agent UI", lifespan=lifespan)

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    generate_report: bool = False


class ChatResponse(BaseModel):
    session_id: str | None = None
    audit_id: str | None = None
    query: str
    skill_name: str
    explanation: str | None = None
    result: dict | None = None
    datasets_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    report_path: str | None = None
    error: str | None = None
    trace: dict | None = None


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    html_path = static_dir / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return "<h1>Factory Agent UI</h1><p>Frontend not found.</p>"


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if harness is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    try:
        response = harness.process_query(
            query=req.query,
            session_id=req.session_id,
            generate_report=req.generate_report,
        )
        return ChatResponse(
            session_id=response.get("session_id"),
            audit_id=response.get("audit_id"),
            query=response.get("query", req.query),
            skill_name=response.get("skill_name", "unknown"),
            explanation=response.get("explanation"),
            result=response.get("result"),
            datasets_used=response.get("datasets_used", []),
            warnings=response.get("warnings", []),
            report_path=response.get("report_path"),
            error=response.get("error"),
            trace=response.get("trace"),
        )
    except Exception as e:
        return ChatResponse(
            query=req.query,
            skill_name="error",
            error=str(e),
        )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok" if harness is not None else "starting",
        "service": "factory-agent",
    }


@app.get("/api/dashboard")
def dashboard() -> JSONResponse:
    if harness is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    try:
        loader = harness._data_loader
        orders = loader.load("orders")
        machines = loader.load("machines")
        inventory = loader.load("inventory")
        process = loader.load("process")

        active_orders = len(orders[orders["status"] == "active"]) if "status" in orders.columns else 0
        urgent_orders = len(orders[orders["priority"] == "urgent"]) if "priority" in orders.columns else 0
        machines_operational = len(machines[machines["status"] == "operational"]) if "status" in machines.columns else 0
        machines_total = len(machines)
        items_low = len(inventory[inventory["quantity_on_hand"] < inventory.get("min_stock_level", 0)])
        total_items = len(inventory)
        total_products = len(process["product_name"].unique()) if "product_name" in process.columns else 0

        return JSONResponse(content={
            "active_orders": active_orders,
            "urgent_orders": urgent_orders,
            "machines_total": machines_total,
            "machines_operational": machines_operational,
            "inventory_items": total_items,
            "items_low_stock": int(items_low),
            "total_products": total_products,
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/tools")
def list_tools() -> JSONResponse:
    if harness is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    tools = harness._tool_registry.definitions()
    return JSONResponse(
        content=[{"name": t.name, "description": t.description} for t in tools]
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=True)
