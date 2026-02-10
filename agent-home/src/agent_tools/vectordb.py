from langchain_core.tools import tool
from typing import List, Optional, Dict
from uuid import uuid4
from base_tools.vertordb import _get_qdrant_client
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
    print(f">>> [Qdrant] 正在将向量写入集合{collection_name}...")
    print(f">>> [Qdrant] 向量数量: {len(vectors)}")
    print(f">>> [Qdrant] 向量维度: {len(vectors[0])}")
    print(f">>> [Qdrant] 向量payloads: {payloads}")
    print(f">>> [Qdrant] 向量ids: {ids}")      
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

