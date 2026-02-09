# -*- coding: utf-8 -*-
import logging
from typing import Any
from models.model import _llm
from agent_tools.tools import ALL_TOOLS
from langchain.agents import create_agent
from agent_states.states import MergeAgentState
from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)

def chat_node(state: MergeAgentState) -> dict[str, Any]:
    """ 
    对话前置过滤器
    :param state: 状态
    :return: 对话结果
    TODO 当前节点属于预留节点，并无实际意义，后续可以考虑删除
    """
    history = state["messages"]
    if not history:
        last_input = state.get("user_input", "")
    else:
        last_input = history[-1].content if hasattr(history[-1], "content") else str(history[-1])
    prompt = f"""
    你是对话前置过滤器。下面是用户最近的一句话：

    {last_input}

    1. 如果你觉得这句话意思不清楚 / 跟任何任务都无关，请委婉说明“我没太理解你的意思”，然后在最后一行输出：ROUTE=none
    2. 如果你觉得这句话有明确需求（比如要天气、新闻、文档等），简单回复一句，然后在最后一行输出：ROUTE=intent_expert

    注意：最后一行必须是单独一行，格式严格为：
    ROUTE=intent_expert
    """
    print(f"    -> [Chat] 提示词: {prompt}")
    # 用历史直接喂给 _llm
    try:
        local_executor = create_agent(_llm, ALL_TOOLS)
        res = local_executor.invoke({"messages": [HumanMessage(content=prompt)]})
        full_text = getattr(res, "content", str(res)) or ""
    except Exception as e:
        logger.error(f"    X [Chat] 发生错误: {e}")
        return {"messages": [AIMessage(content="我没太理解你的意思。")], "chat_route": "none"}
    return {"messages": [AIMessage(content=full_text)], "chat_route": "intent_expert"}