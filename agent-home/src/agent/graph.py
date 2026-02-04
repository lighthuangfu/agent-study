# src/agent/graph.py
from langgraph.graph import StateGraph, END, START
from agent.states import MergeAgentState
from nodes.userintent import intent_agent_node
from nodes.weather import weather_agent_node
from nodes.rss import rss_agent_node
from nodes.mergenode import aggregator_node

# --- 3. 构建图 (Intent Routing Graph) ---
workflow = StateGraph(MergeAgentState)

# 添加节点
workflow.add_node("intent_expert", intent_agent_node)
workflow.add_node("weather_expert", weather_agent_node)
workflow.add_node("rss_expert", rss_agent_node)
workflow.add_node("aggregator", aggregator_node)


def route_from_intent(state: MergeAgentState) -> str:
    """根据意图节点的输出决定后续流向。"""
    route = (state.get("intent_route") or "none").lower()
    if route in ("weather", "rss", "none"):
        return route
    return "none"


# 起点：先做意图理解
workflow.add_edge(START, "intent_expert")

# 根据路由结果选择下一步：
# - weather -> 只跑天气节点
# - rss     -> 只跑 RSS 节点
# - none    -> 直接进入汇总节点，由汇总节点给出“暂不支持”之类的反馈
workflow.add_conditional_edges(
    "intent_expert",
    route_from_intent,
    {
        "weather": "weather_expert",
        "rss": "rss_expert",
        "none": "aggregator",
    },
)

# 天气 / RSS 的结果最终都汇总到 aggregator
workflow.add_edge("weather_expert", "aggregator")
workflow.add_edge("rss_expert", "aggregator")
workflow.add_edge("aggregator", END)

# 编译
graph = workflow.compile()