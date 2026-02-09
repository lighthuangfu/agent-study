# -*- coding: utf-8 -*-

from typing import Any
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime

"""
Doc2Model 是用于存储文档信息的模型，用于存储文档的id、数据、文件key、父文档id、创建时间、更新时间。
"""
class Doc2Model(BaseModel):

    #用户id
    user_id: str = Field(default="用户id不存在")

    #向量数据库中的文档ID
    doc_id: str = Field(default_factory=lambda: str(uuid4()))

    #向量切片生成的图例模板数据，用于存储向量切片生成的图例模板数据（dict/list 等可 JSON 序列化的结构）
    data: dict[str, Any] | list[Any] = Field(default_factory=dict)

    #图例对应图片的存储地址
    file_key: str = Field(default="文件key不存在")

    #切片父级ID，用于存储切片父级ID，可以为空
    parent_doc_id: str = Field(default="父文档id不存在")

    #创建时间
    created_at: datetime = Field(default_factory=datetime.utcnow)

    #更新时间
    updated_at: datetime = Field(default_factory=datetime.utcnow)