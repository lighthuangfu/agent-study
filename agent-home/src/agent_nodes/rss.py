from typing import Any
from models.model import _llm
from agent_tools.tools import ALL_TOOLS
from agent_states.states import MergeAgentState
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from agent.agent_builder import create_custom_agent

# 数据源列表
_rss_urls = [
    "https://sspai.com/feed",
    # "http://www.ruanyifeng.com/blog/atom.xml",
    # "https://plink.anyfeeder.com/weibo/search/hot",
    # "https://plink.anyfeeder.com/newscn/whxw",
    # "https://plink.anyfeeder.com/wsj/cn",
]


def _process_single_url(url: str) -> str:
    """处理单个 RSS URL，返回摘要。"""
    prompt = f"""
    请读取 RSS 源 {url}。
    请列出前 10 篇文章，严格按照以下 Markdown 格式输出，不要包含其他废话：

    1. [文章标题](文章链接)
       - 摘要：简述内容...

    注意：
    - 必须使用 [标题](链接) 的格式隐藏长链接。
    - 摘要部分换行并缩进。
    - 请严格使用 Markdown 格式输出链接，格式为：[标题](URL)。注意：不要在方括号 [] 和圆括号 () 之间加空格。如果标题中包含方括号，请将其转义或替换为其他符号。
    """
    local_executor = create_agent(model=_llm, tools=ALL_TOOLS, name="rss_expert")
    try:
        print(f"    -> 正在抓取: {url}")
        res = local_executor.invoke({"messages": [HumanMessage(content=prompt)]}, config={"configurable": {"langgraph_node": "rss_expert"}})
        content = res["messages"][-1].content
        print(f"    <- 完成: {url}, {content[:60]}...")
        return content
    except Exception as e:
        print(f"    X 失败: {url} | 错误: {e}")
        return f"读取 {url} 失败"


# Node B: RSS 专家（同步顺序调用）
def rss_agent_node(state: MergeAgentState) -> dict[str, Any]:
    print(">>> [RSS Agent] 开始工作 (同步顺序处理...)")
    summaries = []
    for url in _rss_urls:
        summaries.append(_process_single_url(url))
    print(">>> [RSS Agent] 所有 RSS 任务处理完毕")
    return {"rss_summaries": summaries}