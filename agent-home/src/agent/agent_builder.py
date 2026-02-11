# 自定义 ReAct Agent 构建器：可指定「模型」节点名，流式时 langgraph_node 显示该名称而非 "model"
from typing import Annotated, Any, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph import START, StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

def create_custom_agent(
    llm: Any,
    tools: Sequence[Any],
    *,
    model_node_name: str = "assistant",
    tools_node_name: str = "tools",
):
    """
    构建与 create_agent 行为一致的 ReAct 图，但可自定义「模型」节点名。
    流式时 metadata 中的 langgraph_node 将显示 model_node_name，便于区分不同专家。
    """
    from typing import TypedDict

    class _State(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]

    model_with_tools = llm.bind_tools(tools)

    def _call_model(state: _State) -> dict:
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def _should_continue(state: _State) -> str:
        last = state["messages"][-1]
        if getattr(last, "tool_calls", None):
            return "continue"
        return "end"

    workflow = StateGraph(_State)
    workflow.add_node(model_node_name, _call_model)
    workflow.add_node(tools_node_name, ToolNode(tools, name=tools_node_name))

    workflow.add_edge(START, model_node_name)
    workflow.add_conditional_edges(model_node_name, _should_continue, {"continue": tools_node_name, "end": END})
    workflow.add_edge(tools_node_name, model_node_name)

    return workflow.compile()
