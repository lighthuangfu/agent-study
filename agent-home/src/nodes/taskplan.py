# -*- coding: utf-8 -*-
from typing import Any
from models.model import _llm
from agent_states.states import MergeAgentState

def task_plan_node(state: MergeAgentState) -> dict[str, Any]:
    print(">>> [Task Plan] 开始规划任务")
    task_plan = state.get("task_plan", [])
    prompt = f"""
    你是一个“任务规划助手”。现在给你一段用户输入，请你：
    1. 先用 1-2 句话用中文总结用户的核心意图（不要出现“用户意图为”这类前缀）。
    2. 然后根据意图判断用户更像是在要「天气」还是「RSS 新闻」，或者两者都不是。
    3. 如果用户需求与天气和新闻都无关，则选择 ROUTE=doc
    4. 请根据用户意图规划出需要执行的任务，并返回一个任务列表。

    你必须在最后一行，单独输出一个路由标签，格式严格为（只能三选一）：
    - ROUTE=weather
    - ROUTE=rss
    - ROUTE=doc
    用户输入：
    {state.get("user_input", "")}
    """
    res = _llm.invoke(prompt)
    full_text = getattr(res, "content", str(res)) or ""
    lines = [line for line in full_text.splitlines() if line.strip()]
    task_plan = lines[-1].strip()
    print(f"    <- [Task Plan] 任务规划完毕，正在执行任务... \n\n{task_plan}")
    if task_plan == "ROUTE=weather":
        return {"task_plan": {
            "我将进行天气查询计划\n\n",
            "1.加载天气查询软件\n\n",
            "2.查询天气\n\n",
            "3.汇总天气信息\n\n",
            "4.展示天气简报\n\n",
        },
        "user_intent": "weather",
        }
    elif task_plan == "ROUTE=rss":
        return {"task_plan": {
            "我将进行RSS订阅源抓取计划\n\n",
            "1.加载RSS订阅源抓取软件\n\n",
            "2.抓取RSS订阅源\n\n",
            "3.汇总RSS订阅源信息\n\n",
            "4.展示RSS订阅源简报\n\n",
            },
            "user_intent": "rss",
        }
    elif task_plan == "ROUTE=doc":
        return {"task_plan": {
            "我将进行文档查询计划\n\n",
            "1.加载文档查询软件\n\n",
            "2.根据系统知识库查询相关文档\n\n",
            "3.汇总文档信息\n\n",
            "4.展示文档详情\n\n",
        },
        "user_intent": "doc",
        }
    return {"task_plan": task_plan, "user_intent": "doc"}