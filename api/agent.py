"""LangChain tool-calling agent that routes each question to the right tool."""
from typing import Any

from langchain.agents import create_agent
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from .config import (
    AGENT_RECURSION_LIMIT,
    CHROMA_DIR,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_EMBEDDING_MODEL,
    OLLAMA_MODEL,
    OPENAI_EMBEDDING_MODEL,
    OPENAI_MODEL,
)
from .tools import build_tools

SYSTEM_PROMPT = """You are the assistant for Smart Commute Delhi, a Delhi Metro helper.

Rules:
- For routes, travel time, interchanges or the fare of a trip, call get_shortest_route. Never work out routes yourself.
- For DMRC rules, fares slabs, discounts, luggage or timings, call search_dmrc_info.
- For facts about one station (lines, interchange, neighbours), call search_station_info.
- A question can need more than one tool (for example a route plus a luggage rule). Call each one you need.
- Answer only from tool results. If they do not contain the answer, say you don't have that information. Never invent fares, timings or rules.
- The fare in a route result is an estimate; say so. If the DMRC knowledge base gives official slabs, you may mention them as the official reference.
- If a tool reports a station is ambiguous or not found, ask the user to clarify and list the candidates.
- If a typo was auto-corrected (the result has 'corrections'), mention which station you used.
- Be concise. Give routes as a short line-by-line summary, not a list of every stop, unless asked.
"""


def build_agent(
    model: BaseChatModel | None = None,
    embeddings: Embeddings | None = None,
    persist_dir=CHROMA_DIR,
):
    """Create the agent. Uses OpenAI by default, or Ollama when LLM_PROVIDER=ollama."""
    if model is None:
        if LLM_PROVIDER == "ollama":
            from langchain_ollama import ChatOllama

            model = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
        else:
            from langchain_openai import ChatOpenAI

            model = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
    if embeddings is None:
        if LLM_PROVIDER == "ollama":
            from langchain_ollama import OllamaEmbeddings

            embeddings = OllamaEmbeddings(model=OLLAMA_EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)
        else:
            from langchain_openai import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL)
    tools = build_tools(embeddings, persist_dir)
    return create_agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content)


def ask(agent, message: str, history: list[dict] | None = None) -> dict:
    """Run one turn. Returns {"answer": str, "tools_used": [{"name", "args"}...]}."""
    messages = [*(history or []), {"role": "user", "content": message}]
    try:
        result = agent.invoke({"messages": messages}, config={"recursion_limit": AGENT_RECURSION_LIMIT})
    except GraphRecursionError:
        return {
            "answer": "I couldn't finish working that out. Could you rephrase or simplify the question?",
            "tools_used": [],
        }

    tools_used = []
    answer = ""
    for m in result["messages"]:
        if getattr(m, "type", "") == "ai":
            for call in getattr(m, "tool_calls", None) or []:
                tools_used.append({"name": call["name"], "args": call["args"]})
            if _text(m.content).strip():
                answer = _text(m.content)
    return {"answer": answer, "tools_used": tools_used}
