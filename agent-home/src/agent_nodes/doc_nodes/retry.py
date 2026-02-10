from typing import Any
from agent_states.states import MergeAgentState
import logging

logger = logging.getLogger(__name__)

def doc_retry_node(state: MergeAgentState) -> dict[str, Any]:
    state.get
    logger.info(">>> [Doc Retry] 开始工作")
    doc_logs = state.get("doc_logs", [])
    doc_retry_count = state.get("doc_retry_count", 0) + 1
    doc_status = state.get("doc_status", "")
    doc_last_error = state.get("doc_last_error", "")
    if doc_status == "timeout" and doc_retry_count < 3:
        doc_logs.append(f"⚠️ 文档服务超时（已重试 {doc_retry_count} 次）")
    else:
        doc_logs.append(f"⚠️ 文档服务失败（已重试 {doc_retry_count} 次）")
    return _doc_result(doc_logs, doc_retry_count, doc_status, doc_last_error)
    
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