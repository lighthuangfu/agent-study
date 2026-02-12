from typing import Any
from langchain_core.messages import HumanMessage
from models.model import _agent
from agent_states.states import MergeAgentState

def rewrite_doc_node(state: MergeAgentState) -> dict[str, Any]:
    """
    根据 rewrite_instruction 改写 doc，返回新文档。
    仅在中断后用户通过 update_state 传入 rewrite_instruction 时才会进入此节点。
    """
    doc = state.get("doc", "")
    instruction = (state.get("rewrite_instruction") or "").strip()
    if not instruction:
        return {"doc": doc}
    prompt = f"""你是资深编辑。请严格按用户指令改写下方文档，**只输出改写后的完整 Markdown**，不要任何解释。
用户指令：{instruction}
原文档：
{doc}
"""
    result = _agent.invoke({"messages": [HumanMessage(content=prompt)]}, config={"configurable": {"thread_id": "vue_user"}})
    new_doc = result["messages"][-1].content
    return {"doc": new_doc, "rewrite_instruction": ""}  # 清空指令避免重复改写