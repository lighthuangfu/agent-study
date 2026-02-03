
import concurrent.futures

# 引入同级模块
from .tools import ALL_TOOLS
from .model import _llm, model_with_tools 
from langchain.agents import create_agent, AgentState # type: ignore
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


# Node A: 天气专家
def weather_agent_node(state: AgentState):
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
            return result["messages"][-1].content
        except Exception as e:
            return f"天气查询出错: {str(e)}"
        # 使用线程池 + 超时控制 (最多只等 8 秒)
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_weather)
            # 60秒没结果就强制跳过，防止卡死整个系统
            final_msg = future.result(timeout=60)
            print("    <- [Weather] 获取成功")
            return {"weather_report": final_msg}

    except concurrent.futures.TimeoutError:
        print("    X [Weather] 超时！跳过天气查询")
        return {"weather_report": "⚠️ 天气服务响应超时 (跳过)"}
    except Exception as e:
        print(f"    X [Weather] 发生错误: {e}")
        return {"weather_report": "⚠️ 天气服务异常"}

# Node B: RSS 专家
def rss_agent_node(state: AgentState):
    print(">>> [RSS Agent] 开始工作 (启动并发处理...)")
    rss_urls = [
        "https://sspai.com/feed",
        "http://www.ruanyifeng.com/blog/atom.xml",
        "https://plink.anyfeeder.com/weibo/search/hot",
        "https://plink.anyfeeder.com/newscn/whxw",
        "https://plink.anyfeeder.com/wsj/cn"
    ]

    summaries = []

    # 定义一个单独的处理函数，用于单个 URL 的处理
    def process_single_url(url):
        # 注意：这里需要在线程内部重新创建 agent executor，或者确保它是线程安全的
        # 简单起见，我们在这里直接调用工具，或者复用 executor (如果 executor 是无状态的)
        local_executor = create_agent(_llm, ALL_TOOLS)
        prompt = f"""
        请读取 RSS 源 {url}。
        请列出前 10 篇文章，严格按照以下 Markdown 格式输出，不要包含其他废话：

        1. [文章标题](文章链接)
           - 摘要：简述内容...

        注意：
        - 必须使用 [标题](链接) 的格式隐藏长链接。
        - 摘要部分换行并缩进。
        注意：
        - 再次强调：请严格使用 Markdown 格式输出链接，格式为：[标题](URL)。注意：不要在方括号 [] 和圆括号 () 之间加空格。如果标题中包含方括号，请将其转义或替换为其他符号。
        """
        try:
            print(f"    -> 正在抓取: {url}")
            res = local_executor.invoke({"messages": [HumanMessage(content=prompt)]})
            print(f"    <- 完成: {url}")
            return res["messages"][-1].content
        except Exception as e:
            print(f"    X 失败: {url} | 错误: {e}")
            return f"读取 {url} 失败"

    # 使用 ThreadPoolExecutor 进行多线程并发
    # max_workers=5 表示同时开5个线程跑
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # 将任务提交给线程池
        future_to_url = {executor.submit(process_single_url, url): url for url in rss_urls}
        # 等待所有任务完成
        for future in concurrent.futures.as_completed(future_to_url):
            summaries.append(future.result())
    print(">>> [RSS Agent] 所有 RSS 任务处理完毕")
    return {"rss_summaries": summaries}
# Node C: 汇总报告
def aggregator_node(state: AgentState):
    print("\n>>> [Aggregator] 正在汇总最终报告...") # 加个日志确保它跑了
    # 1. 安全获取数据，给默认值防止报错
    weather = state.get("weather_report", "❌ 天气服务暂不可用")
    rss_data = state.get("rss_summaries", [])
    # 2. 调试打印，看看拿到了什么
    print(f"    - 天气数据长度: {len(str(weather))}")
    print(f"    - RSS数据条数: {len(rss_data)}")

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
        for i, summary in enumerate(rss_data, 1):
            final_text += f"\n### 📌 来源 {i}\n{summary}\n"
    # 4. 关键：必须返回 messages，这样 invoke 结果里才有 content
    return {"messages": [AIMessage(content=final_text)]}