import os
from qdrant_client import QdrantClient

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

def _get_qdrant_client() -> QdrantClient:
    """
    内部帮助函数：构造 QdrantClient。
    默认连接本地 6333 端口，支持通过环境变量覆盖：
    - QDRANT_URL
    - QDRANT_API_KEY
    """
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

def _simple_hash_embedding(text: str, dim: int = 384):
    """一个非常简单的本地 embedding 实现，用哈希把文本映射到定长向量。

    说明：这不是“真正的语义向量”，只是为了 demo 先打通“抓网页 → 向量化 → 入库”的流水线，
    以后可以很容易替换成真正的 embedding 模型。
    """
    vec = [0.0] * dim
    if not text:
        return vec

    for ch in text:
        idx = hash(ch) % dim
        vec[idx] += 1.0

    # 简单归一化，避免长度过大
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _split_text_into_chunks(text: str, max_len: int = 500) -> list[str]:
    """把长文本按句子粗略切成若干片段，每段不超过 max_len 字符。"""
    if not text:
        return []
    sentences = re.split(r'(。|！|\!|？|\?)', text)
    chunks: List[str] = []
    current = ""
    for i in range(0, len(sentences), 2):
        sent = sentences[i]
        punct = sentences[i + 1] if i + 1 < len(sentences) else ""
        piece = (sent or "") + (punct or "")
        if len(current) + len(piece) > max_len and current:
            chunks.append(current.strip())
            current = piece
        else:
            current += piece
    if current.strip():
        chunks.append(current.strip())
    return chunks