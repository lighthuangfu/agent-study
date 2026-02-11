from typing import Any
from agent_states.states import MergeAgentState
from langchain_core.messages import AIMessage

def doc_chain_node(state: MergeAgentState) -> dict[str, Any]:
    """
    Doc Chain Node

    Args:
        state: MergeAgentState

    Returns:
        dict[str, Any]
    这个节点主要用于续写文章，执行这个节点之前，确保doc节点已经被成功执行，并且doc节点返回了doc字段
    """
    doc_rewritten = state.get("doc_rewritten", "")
    user_input = state.get("user_input", "")
    user_intent = state.get("user_intent", "")
    prompt = f"""
    你是一个文档续写助手，你的任务是根据用户输入的意图，续写文档。
    用户的意图是：{user_intent}
    用户要续写的内容是：{user_input}
    请根据用户意图和要续写的内容，续写文档。
    注意：
    - 续写的内容必须符合用户意图
    - 续写的内容必须符合用户要续写的内容
    - 续写的内容必须符合用户要续写的内容
    """
    doc_chain_result = state.get("doc_chain_result", [])
    if not doc_chain_result:
        return {"doc_chain_result": doc_chain_result}
    doc_chain_result = "\n".join(doc_chain_result)
    return {"doc_chain_result": doc_chain_result}