# src/agent/graph.py
import logging
from langgraph.graph import StateGraph, END, START
from agent_states.states import MergeAgentState
from agent_nodes.user_intent import intent_agent_node
from agent_nodes.weather import weather_agent_node
from agent_nodes.rss import rss_agent_node
from agent_nodes.doc_nodes.doc import doc_agent_node
from agent_nodes.doc_nodes.retry import doc_retry_node
from agent_nodes.merge_node import aggregator_node
from agent_nodes.task_plan import task_plan_node
from agent_nodes.chat import chat_node

logger = logging.getLogger(__name__)

def _route_from_intent(state: MergeAgentState) -> str:
    """
    根据意图节点的输出决定后续流向。
    """
    route = (state.get("intent_route") or "doc").lower()
    if route in ("weather", "rss", "doc"):
        return route
    return "doc"


def _route_from_doc(state: MergeAgentState) -> str:
    """
    根据文档节点的状态决定是进入重试节点还是直接汇总。
    """
    status = (state.get("doc_status") or "").lower()
    # 只有在明确标记为 timeout 时才进入重试流程，其它情况直接汇总
    if status == "timeout":
        return "retry"
    return "done"


def _route_from_doc_retry(state: MergeAgentState) -> str:
    """
    根据重试节点更新后的状态决定是否再次调用文档节点。
    """
    status = (state.get("doc_status") or "").lower()
    retry_count = int(state.get("doc_retry_count") or 0)
    # 仍然是 timeout 且重试次数小于 3，则继续让 doc_expert 再跑一次
    if status == "timeout" and retry_count < 3:
        return "retry"
    # 否则认为已经结束，进入汇总
    return "done"

def _route_from_chat(state: MergeAgentState) -> str:
    """
    据聊天节点的输出决定后续流向。
    """
    route = (state.get("chat_route") or "none").lower()
    print(f"    <- [route_from_chat Route] 路由: {route}")
    if route in ("none", "intent_expert"):
        return route
    return "none"


#doc子图
doc_graph = StateGraph(MergeAgentState)
doc_graph.add_node("doc_expert", doc_agent_node)
doc_graph.add_node("doc_retry", doc_retry_node)
doc_graph.add_edge(START, "doc_expert")
# 文档节点：成功则结束子图，超时则走重试（子图内只能连到子图节点或 END，不能连主图的 aggregator）
doc_graph.add_conditional_edges(
    "doc_expert",
    _route_from_doc,
    {
        "retry": "doc_retry",
        "done": END,
    },
)
# 重试节点：根据重试后的状态，决定再次调用 doc_expert 还是结束子图
doc_graph.add_conditional_edges(
    "doc_retry",
    _route_from_doc_retry,
    {
        "retry": "doc_expert",
        "done": END,
    },
)
doc_graph = doc_graph.compile()

# --- 3. 构建图 (Intent Routing Graph) ---
workflow = StateGraph(MergeAgentState)

# 添加节点
workflow.add_node("chat", chat_node)
workflow.add_node("intent_expert", intent_agent_node)
workflow.add_node("weather_expert", weather_agent_node)
workflow.add_node("rss_expert", rss_agent_node)
workflow.add_node("aggregator", aggregator_node)
workflow.add_node("task_plan", task_plan_node)
workflow.add_node("doc_graph", doc_graph)

# 起点：先做意图理解
workflow.add_edge(START, "chat")
workflow.add_edge("chat", "intent_expert")
workflow.add_edge("intent_expert", "task_plan")
# 根据路由结果选择下一步：
# - weather -> 只跑天气节点
# - rss     -> 只跑 RSS 节点
# - doc     -> 直接进入文档节点，由文档节点给出文档内容
workflow.add_conditional_edges(
    "task_plan",
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

# 编译
graph = workflow.compile()