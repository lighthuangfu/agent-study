import operator
from typing import TypedDict, Annotated, List
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

    intent_route: str