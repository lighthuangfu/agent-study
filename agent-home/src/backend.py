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
from fastapi.middleware.cors import CORSMiddleware


# 在应用启动时加载 .env 文件中的环境变量
# 这样所有模块都可以通过 os.getenv() 访问这些变量
load_dotenv()

from agent.graph import graph
from agent.rewrite_graph import rewrite_graph
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
    thread_id: Optional[str] = None  # 与 /run-task 的 user_id 一致时，从主图读取 doc 上下文


# 文档生成/改写中断后，用户提交改写指令并继续（支持循环改写）
class DocRewriteContinueRequest(BaseModel):
    thread_id: str  # 必须与 /run-task 时的 user_id 一致
    rewrite_instruction: str  # 改写要求；输入「完成」/「done」则结束改写，进入汇总

# 定义响应数据模型
class TaskResponse(BaseModel):
    result: str
    details: str = ""




@app_server.get("/")
def health_check():
    """探活专用"""
    return {"status": "running"}







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
    async def _event_generator(inputs, thread_id: str = "default_thread"):
        """
        监听 LangGraph 执行过程，并通过 SSE 推送给前端。文档生成/每次改写完成后会中断，可循环调用 /doc-rewrite-and-continue 继续改写，直到用户输入「完成」。
        """

        config = {"configurable": {"thread_id": thread_id}}
        try:
            async for named_event, messages_event, msg_chunks in graph.astream(
                inputs,
                stream_mode=["messages", "updates"],
                subgraphs=True,
                config=config,
            ):
                logger.info("   ----> named_event, messages_event, msg_chunks: %s, %s, %s", named_event, messages_event, msg_chunks)
                if messages_event == "updates":
                    logger.info("msg_chunks %s", msg_chunks)
                elif messages_event == "messages":
                    msg_data = msg_chunks[0]
                    node_name = msg_chunks[1].get("lc_agent_name", "Unknown node")
                    if node_name == "doc_expert" and hasattr(msg_data, "content") and msg_data.content:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': msg_data.content}, ensure_ascii=False)}\n\n"

            # 流结束后检查是否处于中断（文档生成完成，等待改写）
            state = graph.get_state(config)
            if state.next:  # 有待执行节点，说明是 interrupt_after 暂停
                doc = (state.values or {}).get("doc", "")
                logger.info("[interrupt] 文档生成完成，等待用户改写指令，doc 长度=%d", len(doc))
                yield f"data: {json.dumps({'type': 'interrupt', 'doc': doc}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    # 返回流式响应，这样前端就能一点点收到数据了
    return StreamingResponse(
        _event_generator(inputs, user_id),
        media_type="text/event-stream"
    )


@app_server.post("/rewrite-selection")
async def rewrite_selection(request: RewriteRequest):
    """
    独立的改写流程：选中文本 + 可选 hint → 流式返回改写结果。
    使用 LangGraph rewrite_graph 实现。
    """
    text = (request.text or "").strip()
    hint = (request.hint or "").strip()
    thread_id = (request.thread_id or "").strip()
    if not text:
        return StreamingResponse(
            iter([f"data: {json.dumps({'type': 'error', 'message': '选中内容不能为空'}, ensure_ascii=False)}\n\n"]),
            media_type="text/event-stream",
        )

    # 通过 thread 从主图读取 doc 上下文
    doc = ""
    if thread_id:
        config = {"configurable": {"thread_id": thread_id}}
        state = graph.get_state(config)
        logger.info("[rewrite-selection] 从 thread=%s 读取 state: %s", thread_id, state)
        doc = (state.values or {}).get("doc", "")

    async def _rewrite_stream():
        try:
            inputs = {"text": text, "hint": hint, "doc": doc, "result": ""}
            final_result = ""
            async for event in rewrite_graph.astream(
                inputs,
                stream_mode=["messages", "values"],
                config=config,
            ):
                mode, chunk = event[0], event[1]
                if mode == "messages":
                    msg, meta = chunk[0], chunk[1] if isinstance(chunk[1], dict) else {}
                    content = getattr(msg, "content", None)
                    if isinstance(content, str) and content:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': content}, ensure_ascii=False)}\n\n"
                elif mode == "values":
                    final_result = (chunk or {}).get("result", "")
            yield f"data: {json.dumps({'type': 'done', 'result': final_result}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("[rewrite-selection] 改写异常: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(_rewrite_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    # 启动服务，监听 8000 端口
    print("🟢 服务启动中... 请关注此窗口的日志输出")
    uvicorn.run(app_server, host="0.0.0.0", port=8000)