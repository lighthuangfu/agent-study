import requests
from langchain_core.tools import tool
from langchain_community.document_loaders import WebBaseLoader
from base_tools.vertordb import _split_text_into_chunks, _embed_documents
from agent_tools.vectordb import save_vectors_to_qdrant

# 2. 定义 Web Fetch 工具
@tool(description="Fetch the content of a web page directly.")
def web_fetch(url: str) -> str:
    print(f">>> [Web Fetch Tool] 正在抓取网页内容{url}...")
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
    print(f">>> [Web Browser Tool] 正在访问网页P{url}...")
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
    print(f">>> [Index Web] 开始抓取并索引网页{url}...")
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

    # 使用批量向量化（更高效）
    vectors = _embed_documents(chunks)
    payloads = [{"url": url, "text": chunk} for chunk in chunks]

    summary = save_vectors_to_qdrant(
        collection_name=collection_name,
        vectors=vectors,
        payloads=payloads,
    )
    return f"{summary} 网页共切分为 {len(chunks)} 个片段。"
