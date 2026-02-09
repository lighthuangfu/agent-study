import re
import os
import time
import logging
import threading
import concurrent.futures
from typing import Any
from models.model import _llm, api_key
from agent_tools.tools import ALL_TOOLS
from langchain.agents import create_agent
from agent_states.states import MergeAgentState
from langchain_core.messages import HumanMessage
from basetools.dbtool import index_generated_doc_to_qdrant

logger = logging.getLogger(__name__)

base_url = os.environ.get("DOUBAO_BASE_URL")
api_key = os.environ.get("DOUBAO_API_KEY")

# Node D: 文档专家（单次调用 + 超时标记，真正的重试由 graph 中的 doc_retry 节点完成）
def doc_agent_node(state: MergeAgentState) -> dict[str, Any]:
    logger.info(">>> [Doc Agent] 开始工作")
    doc_logs: list[str] = []
    doc_retry_count = int(state.get("doc_retry_count") or 0)
    doc_status = "running"
    doc_last_error = ""

    def _run_doc() -> str:
        """执行文档查询的核心逻辑（不包含重试，仅单次调用）。"""
        user_intent = state.get("user_intent", "")
        if not user_intent:
            msg = "用户需求为空，无法进行文档查询"
            doc_logs.append(msg)
            return msg

        prompt = f"""
        你是高级分析师助手。需要根据用户需求来展示文档内容。用户需求是：{user_intent}
        你可以用以下网址进行资料检索：
        https://huggingface.co/datasets
        https://www.kaggle.com/datasets
        {base_url}?api_key={api_key}
        请直接输出文档内容，按照用户需求展示文档内容。 
        注意：
        - 必须包含具体数据和图表
        - 必须包含具体分析和结论
        - 必须包含具体建议和行动计划
        - 必须包含具体风险和机会
        - 必须包含具体机会和行动计划
        - 不要重复重复的信息
        - 必须用中文显示，这一点要强制执行，不要违反。
        请严格使用 Markdown 格式输出链接，格式为：[标题](URL)。注意：不要在方括号 [] 和圆括号 () 之间加空格。如果标题中包含方括号，请将其转义或替换为其他符号。
        """
        try:
            logger.info(f"    -> 正在创建文档子 Agent，开始调用工具生成内容…\n\n{prompt}")
            doc_executor = create_agent(_llm, ALL_TOOLS)
            doc_logs.append("已创建文档子 Agent，开始调用工具生成内容…")
            result = doc_executor.invoke({"messages": [HumanMessage(content=prompt)]})
            content = result["messages"][-1].content
            log_msg = f"正在获取文档信息的结果预览：{content[:100]}..."
            logger.info(f"    -> {log_msg}")
            doc_logs.append(log_msg)
            return content
        except Exception as e:
            err = f"文档查询出错: {str(e)}"
            doc_logs.append(err)
            raise Exception(err)
        finally:
            doc_logs.append("文档查询完成")
    # 单次调用的超时（秒），真正的重试在 graph 中通过 doc_retry 节点完成
    SINGLE_TIMEOUT = 420
    start_time = time.time()
    msg = ""
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_doc)
            # 等待最多 SINGLE_TIMEOUT 秒
            final_msg = future.result(timeout = SINGLE_TIMEOUT)
            doc_title = _extract_title_from_markdown(final_msg)
            if doc_title:
                logger.info(f"    <- 从 Markdown 提取标题: {doc_title[:80]}...")
                _save_doc_to_qdrant(final_msg, state.get("user_intent", ""), doc_title)
            else:
                logger.info(f"    <- 未提取到标题，使用默认标题")
                doc_title = "未命名文档"
                logger.info(f"    -> 未得到有效标题，使用默认")
                _save_doc_to_qdrant(final_msg, state.get("user_intent", ""), doc_title)
            elapsed = time.time() - start_time
            msg = f"文档节点本次调用成功（用时 {elapsed:.1f}秒）"
            logger.info(f"    <- [Doc] {msg}")
            doc_logs.append(msg)
            doc_status = "success"
            doc_last_error = ""
            return _doc_result(final_msg, doc_logs, doc_retry_count, doc_status, doc_last_error)
    except concurrent.futures.TimeoutError:
        elapsed = time.time() - start_time
        if future.done():
            doc_title = _extract_title_from_markdown(future.result())
            if doc_title:
                logger.info(f"    <- 从 Markdown 提取标题: {doc_title[:80]}...")
                _save_doc_to_qdrant(future.result(), state.get("user_intent", ""), doc_title)
            else:
                logger.info(f"    <- 未提取到标题，使用默认标题")
                doc_title = "未命名文档"
                logger.info(f"    -> 未得到有效标题，使用默认")
            elapsed = time.time() - start_time
            msg = f"文档节点本次调用成功（用时 {elapsed:.1f}秒）"
            logger.info(f"    <- [Doc] {msg}")
            doc_logs.append(msg)
            doc_status = "success"
            doc_last_error = ""
            return _doc_result(future.result(), doc_logs, doc_retry_count, doc_status, doc_last_error)
        else:
            msg = f"文档节点单次调用超时（超过 {SINGLE_TIMEOUT} 秒，总用时 {elapsed:.1f}秒）"
            logger.error(f"    X [Doc] {msg}")
            doc_logs.append(f"⚠️ {msg}")
            doc_status = "timeout"
            doc_last_error = msg
            return _doc_result(future.result(), doc_logs, doc_retry_count, doc_status, doc_last_error)
    except Exception as e:
        elapsed = time.time() - start_time
        msg = f"文档节点调用异常: {e}（用时 {elapsed:.1f}秒）"
        logger.error(f"    X [Doc] {msg}")
        doc_logs.append(f"⚠️ {msg}")
        doc_status = "error"
        doc_last_error = str(e)
        return _doc_result(future.result(), doc_logs, doc_retry_count, doc_status, doc_last_error)
def _extract_title_from_markdown(doc: str) -> str | None:
    """从 Markdown 中提取第一个一级或二级标题。"""
    if not doc or not doc.strip():
        return None
    # 匹配 # 标题 或 ## 标题（去掉 # 和首尾空白）
    m = re.search(r"^#{1,2}\s+(.+)$", doc.strip(), re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None

#保存文章到向量数据库的辅助函数
def _save_doc_to_qdrant(text: str, user_intent: str, doc_title: str):
    try:
        threading.Thread(
            target=index_generated_doc_to_qdrant, 
            args=(
                text, 
                user_intent, 
                doc_title
                )
            ).start()
    except Exception as e:
        logger.error(f"    X [Doc] 索引到 Qdrant 失败: {str(e)}")
    finally:
        logger.info(f"    -> 索引到 Qdrant 完成")

#封装好的结果返回函数
def _doc_result(doc: str, doc_logs: list[str], doc_retry_count: int, doc_status: str, doc_last_error: str)->dict[str, Any]:
    """
    封装好的结果返回函数，用于返回文档节点结果
    :param doc: 文档内容
    :param doc_logs: 文档日志
    :param doc_retry_count: 文档重试次数
    :param doc_status: 文档状态
    :param doc_last_error: 文档最后一次错误信息
    :return: 文档节点结果
    """
    logger.info(f"    <- [Doc] {doc}")
    logger.info(f"    <- [Doc] {doc_logs}")
    logger.info(f"    <- [Doc] {doc_retry_count}")  
    logger.info(f"    <- [Doc] {doc_status}")
    logger.info(f"    <- [Doc] {doc_last_error}")
    return {
        "doc": doc,
        "doc_logs": doc_logs,
        "doc_retry_count": doc_retry_count,
        "doc_status": doc_status,
        "doc_last_error": doc_last_error,
    }