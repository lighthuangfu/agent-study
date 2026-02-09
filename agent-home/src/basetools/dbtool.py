# -*- coding: utf-8 -*-
import os
from uuid import uuid4
from datetime import datetime
from typing import List, Dict
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client import models as qmodels
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


# 尝试导入不同的 embedding 模型
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False

try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

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


# 初始化文本分割器（使用 LangChain 的标准分割器）
_text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,           # 每个 chunk 的最大字符数
    chunk_overlap=50,         # chunk 之间的重叠字符数（保持上下文连贯性）
    length_function=len,      # 计算长度的函数
    separators=["\n\n", "\n", "。", "！", "？", "!", "?", " ", ""],  # 分割符优先级（中文友好）
)


def _split_text_into_chunks(text: str, max_len: int = 500) -> List[str]:
    """
    使用 LangChain 的 RecursiveCharacterTextSplitter 切分文本。
    
    参数:
        text: 要切分的文本
        max_len: 每个 chunk 的最大长度（字符数）
    
    返回:
        文本片段列表
    """
    if not text:
        return []
    
    # 如果指定了不同的 max_len，创建新的分割器
    if max_len != 500:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_len,
            chunk_overlap=min(50, max_len // 10),  # 重叠为 chunk_size 的 10%，最多 50
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "!", "?", " ", ""],
        )
        chunks = splitter.split_text(text)
    else:
        chunks = _text_splitter.split_text(text)
    
    return chunks


def _get_embedding_model() -> Embeddings:
    """
    获取 embedding 模型实例。
    
    优先级：
    1. 如果设置了 EMBEDDING_MODEL 环境变量，使用指定的模型
    2. 如果可用，优先使用 HuggingFace（免费，本地运行，支持中文）
    3. 如果设置了 OPENAI_API_KEY，使用 OpenAI Embeddings
    4. 否则回退到简单的哈希 embedding（仅用于测试）
    
    返回:
        Embeddings 实例
    """
    # 检查是否指定了 embedding 模型
    embedding_model = os.getenv("EMBEDDING_MODEL", "").lower()
    
    # 方案1：使用 HuggingFace（推荐，免费且支持中文）
    if HUGGINGFACE_AVAILABLE and (embedding_model in ("", "huggingface", "hf")):
        try:
            # 使用中文优化的模型，如果没有会自动下载
            # 可选模型：
            # - "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" (多语言，384维)
            # - "sentence-transformers/paraphrase-multilingual-mpnet-base-v2" (多语言，768维)
            # - "shibing624/text2vec-base-chinese" (中文专用，768维)
            model_name = os.getenv(
                "HUGGINGFACE_EMBEDDING_MODEL",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
            print(f"🟢 使用 HuggingFace Embedding 模型: {model_name}")
            return HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu"},  # 使用 CPU，如果有 GPU 可改为 "cuda"
                encode_kwargs={"normalize_embeddings": True}  # 归一化向量
            )
        except Exception as e:
            print(f"⚠️ HuggingFace Embedding 初始化失败: {e}，回退到简单哈希方法")
    
    # 方案2：使用 OpenAI Embeddings（需要 API Key）
    if OPENAI_AVAILABLE and (embedding_model in ("openai", "gpt")):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            print("🟢 使用 OpenAI Embedding 模型")
            return OpenAIEmbeddings(
                model="text-embedding-3-small",  # 或 "text-embedding-3-large"
                openai_api_key=api_key
            )
        else:
            print("⚠️ 未设置 OPENAI_API_KEY，回退到简单哈希方法")
    
    # 方案3：回退到简单的哈希方法（仅用于测试/演示）
    print("⚠️ 使用简单的哈希 Embedding（仅用于测试），建议配置 HuggingFace 或 OpenAI")
    return _SimpleHashEmbeddings(dimension=384)


class _SimpleHashEmbeddings(Embeddings):
    """
    简单的哈希 embedding 实现（仅作为回退方案）。
    这不是真正的语义向量，仅用于测试和演示。
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表。"""
        return [self._embed_text(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本。"""
        return self._embed_text(text)
    
    def _embed_text(self, text: str) -> List[float]:
        """内部方法：将单个文本转换为向量。"""
        import math
        vec = [0.0] * self.dimension
        if not text:
            return vec
        
        for ch in text:
            idx = hash(ch) % self.dimension
            vec[idx] += 1.0
        
        # 简单归一化
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


# 创建全局 embedding 实例（延迟初始化）
_default_embedding: Optional[Embeddings] = None


def _get_default_embedding() -> Embeddings:
    """获取默认的 embedding 实例（延迟初始化）。"""
    global _default_embedding
    if _default_embedding is None:
        _default_embedding = _get_embedding_model()
    return _default_embedding


def _simple_hash_embedding(text: str, dim: int = 384) -> List[float]:
    """
    文本向量化函数（保持向后兼容）。
    
    现在使用成熟的 embedding 模型（HuggingFace/OpenAI），而不是简单的哈希。
    
    参数:
        text: 要向量化的文本
        dim: 向量维度（注意：实际维度取决于使用的 embedding 模型，此参数保留用于兼容性）
    
    返回:
        向量列表
    """
    embedding = _get_default_embedding()
    return embedding.embed_query(text)


def _embed_documents(texts: List[str]) -> List[List[float]]:
    """
    批量向量化文档列表（更高效）。
    
    参数:
        texts: 要向量化的文本列表
    
    返回:
        向量列表的列表
    """
    if not texts:
        return []
    embedding = _get_default_embedding()
    return embedding.embed_documents(texts)

def index_generated_doc_to_qdrant(
    text: str, 
    user_intent: str,
    collection_name: str = "generated_docs"
    ) -> str:
    """
    将生成的文档索引到 Qdrant 向量数据库。
    """
    if not text or not text.strip or not user_intent:
        return "用户意图或文档内容为空，无法进行索引。"

    print(f">>> [Index Generated Doc] 开始索引文档{text[:100]}...")
    print(f">>> [Index Generated Doc] 用户意图: {user_intent}")
    print(f">>> [Index Generated Doc] 文档内容: {text[:100]}...")
    print(f">>> [Index Generated Doc] 集合名称: {collection_name}")
     # 1. 切片
    chunks = _split_text_into_chunks(text, max_len=500)
    if not chunks:
        print(f">>> [Index Generated Doc] 文档切片结果为空，跳过向量入库。")
        return "文档切片结果为空，跳过向量入库。"
    vectors = _embed_documents(chunks)
    doc_id = str(uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    payloads: List[Dict] = []
    for idx, chunk in enumerate(chunks):
        payloads.append(
            {
                "doc_id": doc_id,
                "chunk_id": idx,
                "user_intent": user_intent,
                "source": "generated_doc",
                "created_at": now,
                "text": chunk,
            }
        )
     # 4. 写入 Qdrant（可以复用现有 save_vectors_to_qdrant，或直接用 client）
    client = _get_qdrant_client()
    dim = len(vectors[0])

    try:
        client.get_collection(collection_name)
    except Exception:
        client.recreate_collection(
            collection_name,
            vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
        )

    ids = [str(uuid4()) for _ in vectors]
    points = [
        qmodels.PointStruct(id=pid, vector=vec, payload=pl)
        for pid, vec, pl in zip(ids, vectors, payloads)
    ]
    client.upsert(collection_name=collection_name, points=points)
    return f"已将文档 {doc_id} 的 {len(points)} 个片段写入集合 `{collection_name}`。"


def query_by_doc_id(
    doc_id: str,
    collection_name: str = "generated_docs",
    limit: int = 100,
    with_vectors: bool = False,
) -> List[Dict]:
    """
    按 doc_id 从 Qdrant 集合中查询该文档的所有片段（按 chunk_id 排序）。

    参数:
        doc_id: 文档 ID（写入时 payload 中的 doc_id）
        collection_name: 集合名称，默认 "generated_docs"
        limit: 最多返回条数，默认 100
        with_vectors: 是否返回向量，默认 False

    返回:
        匹配的 point 列表，每项为 {"id": ..., "payload": {...}, "vector": ...(可选)}
    """
    client = _get_qdrant_client()
    try:
        client.get_collection(collection_name)
    except Exception:
        return []

    query_filter = qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="doc_id",
                match=qmodels.MatchValue(value=doc_id),
            )
        ]
    )
    results, _ = client.scroll(
        collection_name=collection_name,
        scroll_filter=query_filter,
        limit=limit,
        with_vectors=with_vectors,
        with_payload=True,
    )
    # 按 chunk_id 排序，便于还原文档顺序
    results.sort(key=lambda p: p.payload.get("chunk_id", 0))
    return [
        {
            "id": p.id,
            "payload": p.payload or {},
            **({"vector": p.vector} if with_vectors and p.vector else {}),
        }
        for p in results
    ]