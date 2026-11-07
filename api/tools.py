"""The three tools the LangChain agent can call.

The tool *descriptions* are what the model reads to decide which tool to use, so they say
explicitly when to use each one and when not to.
"""
import json
from pathlib import Path
from typing import Literal

from langchain_core.embeddings import Embeddings
from langchain_core.tools import BaseTool, tool

from . import rag
from .config import CHROMA_DIR, RETRIEVAL_K
from .metro_client import MetroError
from .planner import plan_route

KB_MISSING = "The knowledge base has not been built yet. Ask the operator to run `make ingest`."


def _format_hits(hits: list[dict]) -> str:
    if not hits:
        return "No relevant information found in the knowledge base."
    return "\n\n".join(f"[source: {h['source']}]\n{h['text']}" for h in hits)


def build_tools(embeddings: Embeddings, persist_dir: Path = CHROMA_DIR, k: int = RETRIEVAL_K) -> list[BaseTool]:
    dmrc_store = rag.get_store(rag.DMRC_COLLECTION, embeddings, persist_dir)
    station_store = rag.get_store(rag.STATION_COLLECTION, embeddings, persist_dir)

    @tool
    def get_shortest_route(
        source: str,
        destination: str,
        mode: Literal["fastest", "least_interchange"] = "fastest",
    ) -> str:
        """Compute a Delhi Metro route between two stations with the Dijkstra routing engine.

        Use for ANY question about how to get from station A to station B: the path, which lines to
        take, where to change, travel time, number of interchanges, or the estimated fare of that trip.
        mode is 'fastest' (default) or 'least_interchange' (fewest line changes).
        Station names may be informal or misspelled; they are resolved automatically. If the result has
        status 'needs_clarification', ask the user which station they meant, listing the candidates.
        Do NOT use for rules, policies, timings or general metro questions.
        """
        try:
            return json.dumps(plan_route(source, destination, mode))
        except MetroError as exc:
            return json.dumps({"status": "error", "message": str(exc)})

    @tool
    def search_dmrc_info(query: str) -> str:
        """Search DMRC rules and passenger information (official fare slabs, smart card and NCMC
        discounts, off-peak hours, luggage limits, prohibited items, general timings).

        Use for policy questions such as 'how much baggage can I carry', 'is there a smart card
        discount' or 'what are the fare slabs'.
        Do NOT use for routes between stations and do NOT use for facts about one specific station.
        """
        if rag.is_empty(dmrc_store):
            return KB_MISSING
        return _format_hits(rag.search(dmrc_store, query, k))

    @tool
    def search_station_info(query: str) -> str:
        """Look up facts about a specific station: which lines serve it, whether it is an interchange,
        neighbouring stations on each line, and coordinates.

        Use for questions like 'which lines pass through Kashmere Gate' or 'what comes after Rajiv
        Chowk on the Blue line'. Do NOT use for routes between two stations or for DMRC rules.
        """
        if rag.is_empty(station_store):
            return KB_MISSING
        return _format_hits(rag.search(station_store, query, k))

    return [get_shortest_route, search_dmrc_info, search_station_info]
