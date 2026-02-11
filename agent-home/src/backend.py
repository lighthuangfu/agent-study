# src/backend.py
import os
import asyncio
import uvicorn
import logging
import json
import urllib3
import langchain
from time import sleep
from fastapi import FastAPI
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from fastapi.middleware.cors import CORSMiddleware


# 在应用启动时加载 .env 文件中的环境变量
# 这样所有模块都可以通过 os.getenv() 访问这些变量
load_dotenv()

from agent.graph import graph
from models.model import _llm

os.environ["USER_AGENT"] = "MyAIUserAgent/1.0"
langchain.debug = True
# 屏蔽警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app_server = FastAPI()

app_server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义请求数据模型 (支持携带用户输入内容)
class TriggerRequest(BaseModel):
    user_id: str = "default_user"
    user_input: Optional[str] = None

# 选中内容改写请求
class RewriteRequest(BaseModel):
    text: str
    hint: Optional[str] = ""  # 用户额外补充说明/续写意图，用于指导改写

# 定义响应数据模型
class TaskResponse(BaseModel):
    result: str
    details: str = ""


async def event_generator(inputs, thread_id: str = "default_thread"):
    """监听 LangGraph 执行过程，并通过 SSE 把关键步骤推送给前端。"""
    try:
       
        async for named_event, messages_event, msg_chunks in graph.astream(
            inputs,
            stream_mode=["messages","updates"],
            subgraphs=True,
            config={"configurable": {"thread_id": thread_id}},
        ):
            if messages_event == 'updates':
                logger.info("msg_chunks %s", msg_chunks)            
            elif messages_event == 'messages': #messages打字机效果
                msg_data = msg_chunks[0] #取出元组数据
                node_name = msg_chunks[1].get('lc_agent_name', 'Unknown node')
                logger.info("node_name %s", node_name)
                target_node = "doc_expert"
                if node_name == target_node:
                    if hasattr(msg_data, 'content') and msg_data.content:
                        content_data = msg_data.content
                        yield f"data: {json.dumps({'type': 'chunk', 'content': content_data}, ensure_ascii=False)}\n\n"
    except Exception as e:
        logger.error(f"Error during streaming: {e}")
        error_data = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
        yield f"data: {error_data}\n\n"

@app_server.get("/")
def health_check():
    return {"status": "running"}


async def _rewrite_stream_generator(text: str, hint: str = ""):
    """调用 LLM 改写选中内容，按 SSE 格式 yield。先尝试流式；若 content 为空则回退为 invoke 再一次性返回。"""
    extra = (hint or "").strip()
    extra_block = ""
    if extra:
        extra_block = f"\n用户补充要求/续写意图：{extra}"
    prompt = f"""请对以下内容进行改写，保持原意、优化表达，使语句更通顺专业。只输出改写后的正文，不要加解释或前缀。
    - 改写后的内容必须符合用户意图
    - 改写后的内容必须符合用户要续写的内容
    - 改写后的内容不能和原内容重复
    原文：
    {text}
    {extra_block}
    """
    logger.info("[rewrite] 改写prompt: %s\n", prompt)
    logger.info("[rewrite] 开始改写，原文长度=%d，预览=%s", len(text), (text[:80] + "…") if len(text) > 80 else text)
    try:
        # 部分兼容 API（如豆包）astream 返回的 chunk.content 可能为空，先尝试流式
        got_any = False
        chunk_count = 0
        full_rewritten: list[str] = []
        async for chunk in _llm.astream([HumanMessage(content=prompt)]):
            content = getattr(chunk, "content", None)
            if isinstance(content, str) and content:
                got_any = True
                chunk_count += 1
                full_rewritten.append(content)
                yield f"data: {json.dumps({'type': 'chunk', 'content': content}, ensure_ascii=False)}\n\n"
        if got_any:
            rewritten_text = "".join(full_rewritten)
            logger.info("[rewrite] 流式改写完成，共推送 %d 个 chunk，全文长度=%d", chunk_count, len(rewritten_text))
            logger.info("[rewrite] 改写后全文内容：\n%s", rewritten_text)
        else:
            # 流式无有效 content 时，用 invoke 拿完整结果再一次性推送
            logger.info("[rewrite] 流式无有效 content，回退为 invoke")
            result = await asyncio.to_thread(
                _llm.invoke,
                [HumanMessage(content=prompt)],
            )
            full = getattr(result, "content", None) or ""
            if full:
                yield f"data: {json.dumps({'type': 'chunk', 'content': full}, ensure_ascii=False)}\n\n"
                logger.info("[rewrite] invoke 回退完成，改写结果长度=%d", len(full))
                logger.info("[rewrite] 改写后全文内容：\n%s", full)
            else:
                logger.warning("[rewrite] invoke 返回内容为空")

        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
        logger.info("[rewrite] 已发送 done")
    except Exception as e:
        logger.exception("[rewrite] 改写异常: %s", e)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"


@app_server.post("/rewrite-selection")
async def rewrite_selection(request: RewriteRequest):
    """根据用户选中的文档内容，流式返回大模型改写结果。"""
    text = (request.text or "").strip()
    hint = (request.hint or "").strip()
    logger.info("[rewrite-selection] 收到请求，选中长度=%d，补充说明长度=%d", len(text), len(hint))
    if not text:
        logger.warning("[rewrite-selection] 选中内容为空，返回错误")
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'message': '选中内容为空'}, ensure_ascii=False)}\n\n"]),
            media_type="text/event-stream",
        )
    return StreamingResponse(
        _rewrite_stream_generator(text, hint),
        media_type="text/event-stream",
    )

@app_server.post("/run-task", response_model=TaskResponse)
async def run_agent_task(request: TriggerRequest):
    logger.info(f"收到请求 user_id={request.user_id}, user_input={request.user_input}")
    user_input = request.user_input or "开始执行任务"
    user_id = request.user_id or "default_user"
    inputs = {
        "messages": [("user", user_input)],
        "rss_data": [],
        "doc": "",
        "weather_report": "",
        "user_input": user_input,
        "user_intent": "",
        "task_plan": [],
    }
    
    # 返回流式响应，这样前端就能一点点收到数据了
    return StreamingResponse(
        event_generator(inputs, user_id), 
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    # 启动服务，监听 8000 端口
    print("🟢 服务启动中... 请关注此窗口的日志输出")
    uvicorn.run(app_server, host="0.0.0.0", port=8000)