import requests
import feedparser
import re
from langchain_core.tools import tool

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
