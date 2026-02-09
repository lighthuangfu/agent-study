# src/agent/graph.py
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from agent_states.states import MergeAgentState
from nodes.userintent import intent_agent_node
from nodes.weather import weather_agent_node
from nodes.rss import rss_agent_node
from nodes.doc_nodes.doc import doc_agent_node
from nodes.doc_nodes.retry import doc_retry_node
from nodes.mergenode import aggregator_node
from nodes.taskplan import task_plan_node
from nodes.chatnodes import chat_node
# --- 3. 构建图 (Intent Routing Graph) ---
workflow = StateGraph(MergeAgentState)

# 添加节点
workflow.add_node("intent_expert", intent_agent_node)
workflow.add_node("weather_expert", weather_agent_node)
workflow.add_node("rss_expert", rss_agent_node)
workflow.add_node("doc_expert", doc_agent_node)
workflow.add_node("doc_retry", doc_retry_node)
workflow.add_node("aggregator", aggregator_node)
workflow.add_node("task_plan", task_plan_node)
workflow.add_node("chat", chat_node)
def route_from_intent(state: MergeAgentState) -> str:
    """根据意图节点的输出决定后续流向。"""
    route = (state.get("intent_route")).lower()
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

def route_from_chat(state: MergeAgentState) -> str:
    """根据聊天节点的输出决定后续流向。"""
    route = (state.get("chat_route") or "none").lower()
    print(f"    <- [route_from_chat Route] 路由: {route}")
    if route in ("none", "intent_expert"):
        return route
    return "none"

# 起点：先做意图理解
workflow.add_edge(START, "chat")
workflow.add_conditional_edges(
    "chat", 
    route_from_chat, 
    {
        "intent_expert": "intent_expert",
    }
)
workflow.add_edge("intent_expert", "task_plan")
# 根据路由结果选择下一步：
# - weather -> 只跑天气节点
# - rss     -> 只跑 RSS 节点
# - doc     -> 直接进入文档节点，由文档节点给出文档内容
workflow.add_conditional_edges(
    "task_plan",
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

# 文档节点：成功则先提取标题再汇总，超时则走重试
workflow.add_conditional_edges(
    "doc_expert",
    route_from_doc,
    {
        "retry": "doc_retry",
        "done": "aggregator",
    },
)
# 标题提取节点完成后进入汇总

# 重试节点：根据重试后的状态，决定再次调用 doc_expert 还是结束到汇总（失败时直接汇总，无标题）
workflow.add_conditional_edges(
    "doc_retry",
    route_from_doc_retry,
    {
        "retry": "doc_expert",
        "done": "aggregator",
    },
)
workflow.add_edge("aggregator", END)

# 本地进程内的记忆（重启进程会丢，但足够做多轮对话）
checkpointer = MemorySaver()

# 编译
graph = workflow.compile()