# src/agent/graph.py
import logging
from langgraph.graph import StateGraph, END, START
from agent_states.states import MergeAgentState
from agent_nodes.user_intent import intent_agent_node
from agent_nodes.weather import weather_agent_node
from agent_nodes.rss import rss_agent_node
from agent_nodes.doc_nodes.doc import doc_agent_node
from agent_nodes.merge_node import aggregator_node
from langgraph.checkpoint.memory import InMemorySaver
from agent_nodes.doc_nodes.interrupt import rewrite_doc_node
from langchain_core.runnables import RunnableLambda

logger = logging.getLogger(__name__)

def _route_from_intent(state: MergeAgentState) -> str:
    """
    根据意图节点的输出决定后续流向。
    """
    route = (state.get("intent_route") or "doc").lower()
    if route in ("weather", "rss", "doc"):
        return route
    return "doc"


def _route_from_doc_interrupt(state: MergeAgentState) -> str:
    """
    文档生成/改写中断后，若用户传入了改写指令则进入改写节点；输入「完成」或空则结束。
    """
    instruction = (state.get("rewrite_instruction") or "").strip().lower()
    if not instruction or instruction in ("完成", "done", "结束", "end"):
        return "end"
    return "rewrite"
checkpointer = InMemorySaver()

#doc子图
doc_graph = StateGraph(MergeAgentState)
doc_graph.add_node("doc_expert", doc_agent_node)
doc_graph.add_edge(START, "doc_expert")
doc_graph.add_edge("doc_expert", END)
doc_graph = doc_graph.compile(checkpointer=checkpointer)

# --- 3. 构建图 (Intent Routing Graph) ---
workflow = StateGraph(MergeAgentState)

# 添加节点
workflow.add_node("intent_expert", intent_agent_node)
workflow.add_node("weather_expert", weather_agent_node)
workflow.add_node("rss_expert", rss_agent_node)
workflow.add_node("aggregator", aggregator_node)
workflow.add_node("doc_graph", doc_graph)
# 起点：先做意图理解
workflow.add_edge(START, "intent_expert")
# 根据路由结果选择下一步：
# - weather -> 只跑天气节点
# - rss     -> 只跑 RSS 节点
# - doc     -> 直接进入文档节点，由文档节点给出文档内容
workflow.add_conditional_edges(
    "intent_expert",
    _route_from_intent,
    {
        "weather": "weather_expert",
        "rss": "rss_expert",
        "doc": "doc_graph",
    },
)

# 天气 / RSS / 文档子图 的结果最终都汇总到 aggregator
workflow.add_edge("weather_expert", "aggregator")
workflow.add_edge("rss_expert", "aggregator")
workflow.add_edge("doc_graph", "aggregator")  # 子图结束后由主图接到 aggregator
workflow.add_edge("aggregator", END)

# 编译（thread_id 在 invoke/astream 时通过 config 传入，用于 checkpoint 隔离）
graph = workflow.compile(checkpointer =checkpointer)