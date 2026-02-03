# src/agent/tools.py
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
import feedparser
import requests
import re

# 1. 定义 Search 工具 (改用 DuckDuckGo，无需 API Key)
# 如果将来有 Tavily Key，可以切回去，那个更精准
search = DuckDuckGoSearchRun() 
# 2. 定义 Web Fetch 工具
@tool
def web_fetch(url: str):
    """
    Fetch the content of a web page directly.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        return response.text[:5000] # Limit content length
    except Exception as e:
        return f"Failed to fetch {url}: {e}"

# 3. 原有的 Web Browser 工具
@tool
def web_browser(url: str):
    """
    访问并读取指定的 URL 网页内容。
    当用户想要了解某个网页、链接或文章的内容时，使用此工具。
    """
    try:
        loader = WebBaseLoader(url)
        docs = loader.load()
        content = docs[0].page_content
        content = " ".join(content.split())
        return content[:5000]
    except Exception as e:
        return f"无法读取该网页，错误信息: {e}"

# 4. 原有的 RSS Reader 工具
@tool
def rss_reader(url: str):
    """
    读取 RSS 订阅源的最新内容。
    增强版：自动处理编码问题、模拟浏览器、处理重定向。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }

    try:
        # verify=False 防止 SSL 证书报错
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        
        # 智能编码检测
        if response.encoding == 'ISO-8859-1' or response.encoding == 'latin-1':
            response.encoding = 'utf-8'
        
        content_data = response.content
        feed = feedparser.parse(content_data)
        
        # 二次尝试解析
        if not feed.entries and feed.bozo:
             try:
                 feed = feedparser.parse(content_data.decode('utf-8'))
             except:
                 pass

        if not feed.entries:
            return f"连接成功 (Status: {response.status_code})，但未解析到文章。可能原因：RSS 格式不标准或被反爬拦截。"

        results = []
        for entry in feed.entries[:5]:
            title = entry.get('title', '无标题')
            link = entry.get('link', '#')
            published = entry.get('published', entry.get('updated', entry.get('created', '时间未知')))
            
            content = ""
            if 'content' in entry:
                content = entry.content[0].value
            elif 'summary_detail' in entry:
                content = entry.summary_detail.value
            else:
                content = entry.get('summary', entry.get('description', '无内容'))

            text_content = re.sub('<[^<]+?>', '', content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            preview = text_content[:1000]
            if len(text_content) > 1000:
                preview += "..."

            results.append(f"""
            【文章标题】{title}
            【发布时间】{published}
            【原文链接】{link}
            【文章内容】{preview}
            """)
            
        return "\n-----------------\n".join(results)

    except Exception as e:
        return f"读取发生错误: {str(e)}"

# 5. 原有的定位工具
@tool
def get_current_location():
    """
    通过 IP 地址获取当前的城市名称。
    返回格式例如：Beijing, China 或 Shanghai
    """
    try:
        # 使用 ip-api.com 的免费接口
        response = requests.get('http://ip-api.com/json/?lang=zh-CN', timeout=5)
        data = response.json()
        if data['status'] == 'success':
            return f"{data['city']}, {data['country']}"
        else:
            return "Unknown Location"
    except Exception as e:
        return f"定位失败: {str(e)}"

# 6. 原有的天气工具
@tool
def get_weather(city: str):
    """
    查询指定城市的天气情况。
    参数 city: 城市名称（如 Beijing, Shanghai）。
    """
    # 让 Agent 去用 search 工具查
    return f"请使用 search 工具去搜索 '{city} current weather' 或 '{city} 天气预报' 来获取数据。"

# --- 汇总导出 ---
ALL_TOOLS = [web_browser, rss_reader, search, web_fetch, get_current_location, get_weather]