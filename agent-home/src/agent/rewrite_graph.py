# 独立的改写流程：选中文本 + 可选 hint → 流式返回改写结果（通过 LangGraph workflow）
from typing import TypedDict
import logging
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
from agent_tools.tools import ALL_TOOLS
from models.model import _llm

logger = logging.getLogger(__name__)

class RewriteState(TypedDict):
    """改写流程的 state，doc 从主图通过 thread 传入"""
    text: str
    hint: str
    doc: str  # 主图 doc 节点的产出，通过 thread 从 graph 获取后传入
    result: str


def _rewrite_node(state: RewriteState, config: RunnableConfig) -> dict:
    """调用 LLM 改写选中内容。可读取 doc 作为上下文，确保改写与文档风格一致。"""
    text = (state.get("text") or "").strip()
    hint = (state.get("hint") or "").strip()
    doc = (state.get("doc") or "").strip()
    logger.info(f"    -> 改写节点收到 doc: {doc[:100]}...")
    if not text:
        return {"result": ""}

    extra_block = f"\n用户补充要求/续写意图：{hint}" if hint else ""
    doc_block = f"\n\n【完整文档上下文：】\n{doc}\n\n【用户选中的原文：】\n" if doc else "\n【原文：】\n"
    prompt = f"""请对以下内容进行改写，保持原意、优化表达，使语句更通顺专业。只输出改写后的正文，不要加解释或前缀。
        - 改写后的内容必须符合用户意图
        - 改写后的内容必须符合用户要续写的内容
        - 改写后的内容不能和原内容重复
        - 若有完整文档上下文，请确保改写后的风格与文档一致
        {doc_block}
        {text}
        {extra_block}
    """
    agent = create_agent(model=_llm, tools=ALL_TOOLS, name="rewrite_doc_expert")
    result = agent.invoke({"messages": [HumanMessage(content=prompt)]}, 
        config={"configurable": {"langgraph_node": "rewrite_doc_expert", "thread_id": "vue_user"}})
    logger.info(f"    -> 改写结果: {result}")
    content = result["messages"][-1].content
    return {"result": content}


# 构建并编译改写图
rewrite_workflow = StateGraph(RewriteState)
rewrite_workflow.add_node("rewrite", _rewrite_node)
rewrite_workflow.add_edge(START, "rewrite")
rewrite_workflow.add_edge("rewrite", END)

rewrite_graph = rewrite_workflow.compile()
