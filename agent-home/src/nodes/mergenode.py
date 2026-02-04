from typing import Any
from agent.states import MergeAgentState
from langchain_core.messages import AIMessage

# Node C: 汇总报告
def aggregator_node(state: MergeAgentState) -> dict[str, Any]:
    print("\n>>> [Aggregator] 正在汇总最终报告...") # 加个日志确保它跑了
    # 1. 安全获取数据，给默认值防止报错
    weather = state.get("weather_report", "❌ 天气服务暂不可用")
    rss_data = state.get("rss_summaries", [])
    user_intent = state.get("user_intent", "")
    # 2. 调试打印，看看拿到了什么
    print(f"    - 天气数据长度: {len(str(weather))}")
    print(f"    - RSS数据条数: {len(rss_data)}")
    print(f"    - 用户意图: {user_intent}")
    # 3. 组装 Markdown
    final_text = f"""
        # 🤖 智能早报 (Agent Output)
        ## 🌤️ 天气情况
        {weather}
        ## 📰 热点订阅 ({len(rss_data)} 源)
        """
    if not rss_data:
        final_text += "\n> ⚠️ 未获取到 RSS 数据，请检查网络或源地址。\n"
    else:
        final_text += f"\n## 🤖 用户意图\n{user_intent}\n"
        for i, summary in enumerate(rss_data, 1):
            final_text += f"\n### 📌 来源 {i}\n{summary}\n"
    # 4. 关键：必须返回 messages，这样 invoke 结果里才有 content
    return {"messages": [AIMessage(content=final_text)]}