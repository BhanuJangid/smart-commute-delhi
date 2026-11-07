import json

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from api import rag
from api.agent import ask, build_agent
from api.tools import KB_MISSING, build_tools
from tests.conftest import needs_binary


class StubToolModel(GenericFakeChatModel):
    """Scripted chat model that accepts bind_tools, so the real agent loop runs without an LLM."""

    def bind_tools(self, tools, **kwargs):
        return self


def _call(name, args, call_id="c1"):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def _tools(tmp_path, emb):
    return {t.name: t for t in build_tools(emb, tmp_path)}


@needs_binary
def test_route_tool_returns_json_and_flags_ambiguity(tmp_path, fake_embeddings):
    tools = _tools(tmp_path, fake_embeddings)
    ok = json.loads(tools["get_shortest_route"].invoke({"source": "rajeev chowk", "destination": "Dwarka"}))
    assert ok["status"] == "ok" and ok["corrections"]["source"]["used"] == "Rajiv Chowk"

    amb = json.loads(tools["get_shortest_route"].invoke({"source": "airport", "destination": "AIIMS"}))
    assert amb["status"] == "needs_clarification"


def test_retrieval_tools_report_missing_knowledge_base(tmp_path, fake_embeddings):
    tools = _tools(tmp_path, fake_embeddings)
    assert tools["search_dmrc_info"].invoke({"query": "luggage"}) == KB_MISSING
    assert tools["search_station_info"].invoke({"query": "Kashmere Gate"}) == KB_MISSING


def test_retrieval_tools_return_sourced_text_after_ingest(tmp_path, fake_embeddings):
    rag.ingest(fake_embeddings, tmp_path)
    tools = _tools(tmp_path, fake_embeddings)
    assert "[source:" in tools["search_dmrc_info"].invoke({"query": "luggage weight limit"})
    assert "[source: stations.csv]" in tools["search_station_info"].invoke({"query": "Kashmere Gate"})


@needs_binary
def test_agent_loop_executes_tool_and_reports_it(tmp_path, fake_embeddings):
    model = StubToolModel(
        messages=iter(
            [
                _call("get_shortest_route", {"source": "Rajiv Chowk", "destination": "Dwarka"}),
                AIMessage(content="Take the Blue line straight through, about 44 minutes."),
            ]
        )
    )
    agent = build_agent(model=model, embeddings=fake_embeddings, persist_dir=tmp_path)
    out = ask(agent, "How do I get from Rajiv Chowk to Dwarka?")
    assert out["answer"].startswith("Take the Blue line")
    assert out["tools_used"] == [
        {"name": "get_shortest_route", "args": {"source": "Rajiv Chowk", "destination": "Dwarka"}}
    ]
