# src/agent/graph.py
from langgraph.graph import StateGraph, END, START
from agent_states.states import MergeAgentState
from nodes.userintent import intent_agent_node
from nodes.weather import weather_agent_node
from nodes.rss import rss_agent_node
from nodes.doc_nodes.doc import doc_agent_node
from nodes.doc_nodes.retry import doc_retry_node
from nodes.mergenode import aggregator_node

# --- 3. 构建图 (Intent Routing Graph) ---
workflow = StateGraph(MergeAgentState)

# 添加节点
workflow.add_node("intent_expert", intent_agent_node)
workflow.add_node("weather_expert", weather_agent_node)
workflow.add_node("rss_expert", rss_agent_node)
workflow.add_node("doc_expert", doc_agent_node)
workflow.add_node("doc_retry", doc_retry_node)
workflow.add_node("aggregator", aggregator_node)

def route_from_intent(state: MergeAgentState) -> str:
    """根据意图节点的输出决定后续流向。"""
    route = (state.get("intent_route") or "none").lower()
    if route in ("weather", "rss", "doc"):
        return route
    return "doc"


def route_from_doc(state: MergeAgentState) -> str:
    """根据文档节点的状态决定是进入重试节点还是直接汇总。"""
    status = (state.get("doc_status") or "").lower()
    # 只有在明确标记为 timeout 时才进入重试流程，其它情况直接汇总
    if status == "timeout":
        return "retry"
    return "done"


def route_from_doc_retry(state: MergeAgentState) -> str:
    """根据重试节点更新后的状态决定是否再次调用文档节点。"""
    status = (state.get("doc_status") or "").lower()
    retry_count = int(state.get("doc_retry_count") or 0)
    # 仍然是 timeout 且重试次数小于 3，则继续让 doc_expert 再跑一次
    if status == "timeout" and retry_count < 3:
        return "retry"
    # 否则认为已经结束，进入汇总
    return "done"


# 起点：先做意图理解
workflow.add_edge(START, "intent_expert")

# 根据路由结果选择下一步：
# - weather -> 只跑天气节点
# - rss     -> 只跑 RSS 节点
# - doc     -> 直接进入文档节点，由文档节点给出文档内容
workflow.add_conditional_edges(
    "intent_expert",
    route_from_intent,
    {
        "weather": "weather_expert",
        "rss": "rss_expert",
        "doc": "doc_expert",
    },
)

# 天气 / RSS 的结果最终都汇总到 aggregator
workflow.add_edge("weather_expert", "aggregator")
workflow.add_edge("rss_expert", "aggregator")

# 文档节点：先跑 doc_expert，再根据状态走重试或汇总
workflow.add_conditional_edges(
    "doc_expert",
    route_from_doc,
    {
        "retry": "doc_retry",
        "done": "aggregator",
    },
)

# 重试节点：根据重试后的状态，决定再次调用 doc_expert 还是结束到汇总
workflow.add_conditional_edges(
    "doc_retry",
    route_from_doc_retry,
    {
        "retry": "doc_expert",
        "done": "aggregator",
    },
)

workflow.add_edge("aggregator", END)

# 编译
graph = workflow.compile()  