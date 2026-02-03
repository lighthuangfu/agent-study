# src/agent/graph.py
import sys
import os

from langchain.agents import AgentState
from agent.nodes import weather_agent_node, rss_agent_node, aggregator_node
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END, START

# --- 路径补丁 (防止相对导入报错) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)


# --- 3. 构建图 (Parallel Graph) ---
workflow = StateGraph(AgentState)

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