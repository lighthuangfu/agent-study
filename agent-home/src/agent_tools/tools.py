# src/agent/tools.py
from langchain_community.tools import DuckDuckGoSearchRun
from agent_tools.webprocess import web_fetch
from agent_tools.webprocess import web_browser
from agent_tools.rss import rss_reader
from agent_tools.location import get_current_location
from agent_tools.weather import get_weather
from agent_tools.vectordb import save_vectors_to_qdrant
from agent_tools.webprocess import index_web_page_to_qdrant



# 1. 定义 Search 工具 (改用 DuckDuckGo，无需 API Key)
# 如果将来有 Tavily Key，可以切回去，那个更精准
search = DuckDuckGoSearchRun() 

# --- 汇总导出 ---
ALL_TOOLS = [
    web_browser,
    rss_reader,
    search,
    web_fetch,
    get_current_location,
    get_weather,
    save_vectors_to_qdrant,
    index_web_page_to_qdrant,
]