import operator
from typing import Annotated, List, TypedDict, Sequence
from langchain_core.messages import BaseMessage

# --- 1. 定义状态 ---
class AgentState(TypedDict):
    # messages: 聊天的历史记录
    messages: Annotated[Sequence[BaseMessage], operator.add]
    # weather_report: 专门存天气结果
    weather_report: str
    # rss_summaries: 专门存 RSS 结果列表
    rss_summaries: Annotated[List[str], operator.add]