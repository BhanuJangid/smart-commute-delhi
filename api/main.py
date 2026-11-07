"""FastAPI service: REST endpoints over the C++ router plus a /chat endpoint backed by the agent."""
import os
import time
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from . import metro_client
from .agent import ask, build_agent
from .config import LLM_PROVIDER, METRO_BIN
from .network import load_stations
from .planner import plan_route
from .stations import search as search_stations

app = FastAPI(
    title="Smart Commute Delhi API",
    description="Dijkstra routing (C++ engine) plus a LangChain agent with RAG over DMRC information.",
    version="1.0.0",
)

Mode = Literal["fastest", "least_interchange"]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class ToolCall(BaseModel):
    name: str
    args: dict


class ChatResponse(BaseModel):
    answer: str
    tools_used: list[ToolCall]
    latency_ms: int


@lru_cache(maxsize=1)
def get_agent():
    return build_agent()


def _raise_for_problem(result: dict) -> None:
    status = result["status"]
    if status == "not_found":
        raise HTTPException(404, detail=result["problems"])
    if status == "needs_clarification":
        raise HTTPException(409, detail=result["problems"])
    if status == "same_station":
        raise HTTPException(422, detail="Source and destination are the same station.")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "engine_built": METRO_BIN.exists(),
        "stations": len(load_stations()),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "llm_provider": LLM_PROVIDER,
    }


@app.get("/stations")
def stations(q: str = Query("", description="Optional name to search for (fuzzy).")) -> list[dict]:
    return [
        {"id": s.id, "name": s.name, "lines": list(s.lines), "match_score": round(score, 1)}
        for s, score in search_stations(q, limit=10 if q else 50)
    ]


@app.get("/route")
def route(src: str, dst: str, mode: Mode = "fastest") -> dict:
    try:
        result = plan_route(src, dst, mode)
    except metro_client.MetroBinaryMissing as exc:
        raise HTTPException(503, detail=str(exc)) from exc
    except metro_client.MetroError as exc:
        raise HTTPException(500, detail=str(exc)) from exc
    _raise_for_problem(result)
    if result["status"] == "no_route":
        raise HTTPException(404, detail="No route found between these stations.")
    return result


@app.get("/fare")
def fare(src: str, dst: str) -> dict:
    result = route(src, dst, "fastest")
    return {
        "from": result["from"],
        "to": result["to"],
        "fare_inr": result["fare_inr"],
        "stations": result["stations"],
        "minutes": result["minutes"],
        "note": result["fare_note"],
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if LLM_PROVIDER == "ollama":
        pass
    elif not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503, detail="OPENAI_API_KEY is not set. Add it to .env to enable /chat.")
    start = time.perf_counter()
    try:
        out = ask(get_agent(), req.message, [t.model_dump() for t in req.history])
    except Exception as exc:
        detail = (
            "LLM backend is unavailable. "
            f"Provider='{LLM_PROVIDER}'. "
            "Start the local server or set a valid API key."
        )
        raise HTTPException(503, detail=detail) from exc
    return ChatResponse(
        answer=out["answer"],
        tools_used=[ToolCall(**t) for t in out["tools_used"]],
        latency_ms=round((time.perf_counter() - start) * 1000),
    )
