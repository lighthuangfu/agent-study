from typing import Any
from models.model import _llm
from agent.states import MergeAgentState

def intent_agent_node(state: MergeAgentState) -> dict[str, Any]:
    print(">>> [Intent Agent] 开始解析用户意图")
    raw_input = state.get("user_input", "") or ""

    if not raw_input:
        intent_text = "用户未提供额外输入，执行默认的每日资讯早报任务。"
        print(f"    -> 无用户输入，使用默认意图: {intent_text}")
        # 没有明确输入时，不强制跑天气或 RSS，由后续默认逻辑决定
        return {"user_intent": intent_text, "intent_route": "none"}

    prompt = f"""
        你是一个“用户意图理解助手 + 路由器”。现在给你一段用户输入，请你：
        1. 先用 1-2 句话用中文总结用户的核心意图（不要出现“用户意图为”这类前缀）。
        2. 然后根据意图判断用户更像是在要「天气」还是「RSS 新闻」，或者两者都不是。

        你必须在最后一行，单独输出一个路由标签，格式严格为（只能三选一）：
        - ROUTE=weather
        - ROUTE=rss
        - ROUTE=none

        其中：
        - 当用户主要关心天气、温度、下雨、穿衣等信息时，选择 ROUTE=weather
        - 当用户想看新闻、资讯、热点、RSS 等内容时，选择 ROUTE=rss
        - 当用户需求与天气和新闻都无关时，选择 ROUTE=none

        用户输入：
        {raw_input}
        """
    try:
        res = _llm.invoke(prompt)
        full_text = getattr(res, "content", str(res)) or ""
        lines = [line for line in full_text.splitlines() if line.strip()]

        route = "none"
        # 从最后一行中解析 ROUTE
        if lines:
            last_line = lines[-1].strip()
            if last_line.upper().startswith("ROUTE="):
                route = last_line.split("=", 1)[1].strip().lower() or "none"
                lines = lines[:-1]  # 剩余部分作为意图总结

        intent_text = "\n".join(lines).strip() or "未能解析出清晰的用户意图。"

        # 基于关键字进行一次“纠错式”路由判断，避免模型选错
        text_for_rule = (raw_input + "\n" + intent_text).lower()
        has_weather_kw = any(k in text_for_rule for k in ["天气", "气温", "下雨", "温度"])
        has_rss_kw = any(k in text_for_rule for k in ["rss", "新闻", "资讯", "头条", "热点"])

        if has_weather_kw and not has_rss_kw:
            route = "weather"
        elif has_rss_kw and not has_weather_kw:
            route = "rss"

        print(f"    <- 解析到的用户意图：{intent_text[:80]}...")
        print(f"    <- 路由决策：{route}")
    except Exception as e:
        intent_text = f"意图理解失败：{e}"
        route = "none"
        print(f"    X [Intent Agent] 发生错误: {e}")

    return {"user_intent": intent_text, "intent_route": route}