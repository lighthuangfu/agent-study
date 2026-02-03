# src/agent/graph.py
import sys
import os
from langgraph.graph import StateGraph, END, START
from agent.nodes import weather_agent_node, rss_agent_node, aggregator_node
from agent.states import MergeAgentState




# --- 3. 构建图 (Parallel Graph) ---
workflow = StateGraph(MergeAgentState)

# 添加节点
workflow.add_node("weather_expert", weather_agent_node)
workflow.add_node("rss_expert", rss_agent_node)
workflow.add_node("aggregator", aggregator_node)

# 定义并行流向
workflow.add_edge(START, "weather_expert")
workflow.add_edge(START, "rss_expert")

workflow.add_edge("weather_expert", "aggregator")
workflow.add_edge("rss_expert", "aggregator")

workflow.add_edge("aggregator", END)

# 编译
graph = workflow.compile()