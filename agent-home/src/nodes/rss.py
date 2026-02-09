import concurrent.futures
from typing import Any
from models.model import _llm
from agent_tools.tools import ALL_TOOLS
from agent_states.states import MergeAgentState
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

#数据源列表
_rss_urls = [
        "https://sspai.com/feed",
        "http://www.ruanyifeng.com/blog/atom.xml",
        "https://plink.anyfeeder.com/weibo/search/hot",
        "https://plink.anyfeeder.com/newscn/whxw",
        "https://plink.anyfeeder.com/wsj/cn"
    ]
# Node B: RSS 专家
def rss_agent_node(state: MergeAgentState) -> dict[str, Any]:
    print(">>> [RSS Agent] 开始工作 (启动并发处理...)")
    summaries = []
    # 定义一个单独的处理函数，用于单个 URL 的处理
    def process_single_url(url: str) -> str:
        """
        处理单个 RSS URL
        :param url: RSS URL
        :return: RSS 摘要
        注意：这里需要在线程内部重新创建 agent executor，或者确保它是线程安全的
        简单起见，我们在这里直接调用工具，或者复用 executor (如果 executor 是无状态的)
        """
        
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
        local_executor = create_agent(_llm, ALL_TOOLS)
        try:
            print(f"    -> 正在抓取: {url}")
            res = local_executor.invoke({"messages": [HumanMessage(content=prompt)]})
            print(f"    <- 完成: {url}, {res['messages'][-1].content[:60]}...")
            return res["messages"][-1].content
        except Exception as e:
            print(f"    X 失败: {url} | 错误: {e}")
            return f"读取 {url} 失败"

    # 使用 ThreadPoolExecutor 进行多线程并发
    # max_workers=5 表示同时开5个线程跑
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # 将任务提交给线程池
        future_to_url = {executor.submit(process_single_url, url): url for url in _rss_urls}
        # 等待所有任务完成
        for future in concurrent.futures.as_completed(future_to_url):
            summaries.append(future.result())
    print(f">>> [RSS Agent] 所有 RSS 任务处理完毕: {summaries[:100]}")
    return {"rss_summaries": summaries}