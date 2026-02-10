# -*- coding: utf-8 -*-
import logging
from typing import Any
from agent_states.states import MergeAgentState

logger = logging.getLogger(__name__)

def chat_node(state: MergeAgentState) -> dict[str, Any]:
    """ 
    对话前置过滤器
    :param state: 状态
    :return: 对话结果
    TODO 当前节点属于预留节点，并无实际意义，后续可以考虑删除
    """
    logger.info("->[Chat]这是一个空节点,用于测试节点流转")
    return {"messages":["第一个空节点"], "chat_route": "intent_expert"}