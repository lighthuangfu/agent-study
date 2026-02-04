from typing import Any
from agent_states.states import MergeAgentState

def doc_retry_node(state: MergeAgentState) -> dict[str, Any]:
    print(">>> [Doc Retry] 开始工作")
    doc_logs = state.get("doc_logs", [])
    doc_retry_count = state.get("doc_retry_count", 0) + 1
    doc_status = state.get("doc_status", "")
    doc_last_error = state.get("doc_last_error", "")
    if doc_status == "timeout" and doc_retry_count < 3:
        doc_logs.append(f"⚠️ 文档服务超时（已重试 {doc_retry_count} 次）")
        return {
            "doc_logs": doc_logs,
            "doc_retry_count": doc_retry_count,
            "doc_status": doc_status,
            "doc_last_error": doc_last_error,
        }
    else:
        doc_logs.append(f"⚠️ 文档服务失败（已重试 {doc_retry_count} 次）")
        return {
            "doc_logs": doc_logs,
            "doc_retry_count": doc_retry_count,
            "doc_status": doc_status,
            "doc_last_error": doc_last_error,
        }