from langchain_core.tools import tool
# 6. 原有的天气工具
@tool(description="Get the current weather information for a specified city.")
def get_weather(city: str):
    """
    查询指定城市的天气情况。
    参数 city: 城市名称（如 Beijing, Shanghai）。
    """
    # 让 Agent 去用 search 工具查
    return f"请使用 search 工具去搜索 '{city} current weather' 或 '{city} 天气预报' 来获取数据。"

