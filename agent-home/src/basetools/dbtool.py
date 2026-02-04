# -*- coding: utf-8 -*-
import os
from typing import List, Optional
from qdrant_client import QdrantClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.embeddings import Embeddings

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