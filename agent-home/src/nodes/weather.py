import concurrent.futures
from typing import Any
from models.model import _llm
from agent_tools.tools import ALL_TOOLS
from agent.states import MergeAgentState
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

# Node A: 天气专家
def weather_agent_node(state: MergeAgentState) -> dict[str, Any]:
    print(">>> [Weather Agent] 开始工作")
    def _run_weather():
        prompt = """
        你是天气助手。需要根据定位来展示实时气温和24小时预报。
        如果发现是国内IP，则无需修改查询城市，如果发现IP是不在中国大陆，则强制修正为北京。
        必须包含具体温度数字。
        请直接输出简报内容，不要废话
        用中文显示。
        """
        try:
            weather_executor = create_agent(_llm, ALL_TOOLS)
            # 执行子任务
            result = weather_executor.invoke({"messages": [HumanMessage(content=prompt)]})
            print(f"    -> 正在获取天气信息的结果是：{result['messages'][-1].content[:160]}.")
            return result["messages"][-1].content
        except Exception as e:
            return f"天气查询出错: {str(e)}"
        # 使用线程池 + 超时控制 (最多只等 8 秒)
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_weather)
            # 240秒没结果就强制跳过，防止卡死整个系统
            final_msg = future.result(timeout=240)
            print(f"    <- [Weather] 获取成功:{final_msg[:120]}...")
            return {"weather_report": final_msg}

    except concurrent.futures.TimeoutError:
        print("    X [Weather] 超时！跳过天气查询")
        return {"weather_report": "⚠️ 天气服务响应超时 (跳过)"}
    except Exception as e:
        print(f"    X [Weather] 发生错误: {e}")
        return {"weather_report": "⚠️ 天气服务异常"}