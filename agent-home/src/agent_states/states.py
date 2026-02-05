import operator
from typing import TypedDict, Annotated, List, Dict
from langchain_core.messages import BaseMessage

# 1. 定义自定义 State
class MergeAgentState(TypedDict):
    # messages 是标准字段，使用 addReducer (operator.add) 使得并行分支的消息能合并
    messages: Annotated[List[BaseMessage], operator.add]
    
    # 自定义字段：存放 RSS 列表
    # 如果两个分支都写入这个字段，可以用 operator.add；这里只有一个分支写，直接定义即可
    rss_summaries: List[str] 
    
    # 自定义字段：存放天气报告
    weather_report: str

    # 自定义字段：原始用户输入
    user_input: str

    # 自定义字段：模型解析后的用户意图
    user_intent: str

    

    # 自定义字段：路由决策
    intent_route: str

    # 自定义字段：任务规划
    task_plan: Dict[str, List[str]]

    # 自定义字段：文档节点的重试与超时日志
    doc_logs: List[str]

    # 自定义字段：文档节点的重试次数
    doc_retry_count: int

    # 自定义字段：文档节点当前状态（running/success/timeout/error）
    doc_status: str

    # 自定义字段：文档节点最后一次错误信息
    doc_last_error: str

    doc: str