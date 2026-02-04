# src/agent/tools.py
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from basetools.dbtool import _get_qdrant_client, _simple_hash_embedding, _split_text_into_chunks
import feedparser
import requests
import re
from typing import List, Optional, Dict
from uuid import uuid4

# 1. 定义 Search 工具 (改用 DuckDuckGo，无需 API Key)
# 如果将来有 Tavily Key，可以切回去，那个更精准
search = DuckDuckGoSearchRun() 
# 2. 定义 Web Fetch 工具
@tool(description="Fetch the content of a web page directly.")
def web_fetch(url: str) -> str:
    print(">>> [Web Fetch Tool] 正在抓取网页内容...")
    """
    Fetch the content of a web page directly.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        return response.text[:5000]  # 返回前5000字符
    except Exception as e:
        return f"Failed to fetch {url}: {e}"

# 3. 原有的 Web Browser 工具
@tool(description="Browse and read the content of a web page.")
def web_browser(url: str) -> str:
    print(">>> [Web Browser Tool] 正在访问网页...")
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
@tool(description="Read and summarize the latest content from an RSS feed URL.")
def rss_reader(url: str) -> str:
    print(">>> [RSS Reader Tool] 正在读取 RSS 内容...")
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
@tool(description="Get the current city location based on IP address.")
def get_current_location():
    print(">>> [Location Tool] 正在获取当前城市信息...")
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
@tool(description="Get the current weather information for a specified city.")
def get_weather(city: str):
    """
    查询指定城市的天气情况。
    参数 city: 城市名称（如 Beijing, Shanghai）。
    """
    # 让 Agent 去用 search 工具查
    return f"请使用 search 工具去搜索 '{city} current weather' 或 '{city} 天气预报' 来获取数据。"


@tool(
    description=(
        "将已经计算好的向量写入 Qdrant 向量数据库。\n"
        "参数说明：\n"
        "- collection_name: Qdrant 集合名称，若不存在会自动创建\n"
        "- vectors: 向量列表，每个元素是一个浮点数组，例如 [[0.1, 0.2, ...], ...]\n"
        "- payloads: 可选的 payload 列表，与 vectors 一一对应，用于存放元数据（如 url、文本片段等）\n"
        "- ids: 可选的 ID 列表，若不提供则自动生成 UUID"
    )
)
def save_vectors_to_qdrant(
    collection_name: str,
    vectors: List[List[float]],
    payloads: Optional[List[Dict]] = None,
    ids: Optional[List[str]] = None,
) -> str:
    """
    将一批向量写入 Qdrant：
    - 如果集合不存在，会自动根据首个向量的维度创建集合（使用 COSINE 距离）。
    - 写入完成后返回写入的向量条数。
    """
    if not vectors:
        print(">>> [Qdrant] 未收到任何向量，已跳过写入。")
        return "未收到任何向量，已跳过写入。"

    dim = len(vectors[0])
    client = _get_qdrant_client()

    # 确保集合存在
    try:
        client.get_collection(collection_name)
    except Exception:
        client.recreate_collection(
            collection_name,
            vectors_config = client.models.VectorParams(size=dim, distance=client.models.Distance.COSINE),
        )

    # 处理 IDs
    if ids is None or len(ids) != len(vectors):
        ids = [str(uuid4()) for _ in vectors]

    # 处理 payloads
    if payloads is None:
        payloads = [{} for _ in vectors]
    elif len(payloads) != len(vectors):
        # 长度不一致时，简单截断或填充
        payloads = (payloads + [{}] * len(vectors))[: len(vectors)]

    points = [
        client.models.PointStruct(id=pid, vector=vec, payload=pl)
        for pid, vec, pl in zip(ids, vectors, payloads)
    ]

    client.upsert(collection_name=collection_name, points=points)
    return f"成功写入 {len(points)} 条向量到 Qdrant 集合 `{collection_name}` 中。"





@tool(
    description=(
        "抓取指定网页内容，进行简单切分和向量化，并将结果写入本地 Qdrant 向量数据库。\n"
        "适合作为 Demo：先打通“网页 → 向量库”链路，后续可以替换为真实的 embedding 模型。\n"
        "参数：\n"
        "- url: 需要索引的网页地址\n"
        "- collection_name: 向量集合名称，默认 'web_pages'"
    )
)
def index_web_page_to_qdrant(url: str, collection_name: str = "web_pages") -> str:
    """
    流程：
    1. 使用 web_browser 抓取网页正文；
    2. 将正文切分为多个片段；
    3. 对每个片段做简单向量化；
    4. 调用 save_vectors_to_qdrant 写入 Qdrant。
    """
    print(">>> [Index Web] 开始抓取并索引网页:", url)
    raw_text = web_browser(url)
    if not raw_text or "错误" in str(raw_text):
        return f"抓取网页失败: {raw_text}"

    chunks = _split_text_into_chunks(str(raw_text), max_len=500)
    if not chunks:
        return "网页抓取成功，但未得到有效文本内容。"

    vectors = [_simple_hash_embedding(chunk) for chunk in chunks]
    payloads = [{"url": url, "text": chunk} for chunk in chunks]

    summary = save_vectors_to_qdrant(
        collection_name=collection_name,
        vectors=vectors,
        payloads=payloads,
    )
    return f"{summary} 网页共切分为 {len(chunks)} 个片段。"

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