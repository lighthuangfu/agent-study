# src/backend.py
import os
import uvicorn
import logging
import json
import asyncio
import urllib3
import langchain
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# 在应用启动时加载 .env 文件中的环境变量
# 这样所有模块都可以通过 os.getenv() 访问这些变量
load_dotenv()

from agent.graph import graph
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

# 定义响应数据模型
class TaskResponse(BaseModel):
    result: str
    details: str = ""

async def event_generator(inputs):
    """
    这是一个生成器，负责监听 LangGraph 的运行步骤，
    并把每一步的状态实时推送到前端。
    """
    """
    这是一个生成器，负责监听 LangGraph 的运行步骤，
    并把每一步的状态实时推送到前端（SSE）。
    """
    try:
        # 使用 astream (异步流) 代替 invoke
        async for event in graph.astream(inputs):
            for node_name, state in event.items():
                logger.info("asteam 异步流信息日志, node_name=%s, state_keys=%s", node_name, list(state.keys()))

                # 先处理特殊节点：意图理解，单独推送一条 intent 事件
                if node_name == "intent_expert":
                    intent_text = state.get("user_intent") or ""
                    intent_route = state.get("intent_route") or "none"
                    if intent_text:
                        intent_data = json.dumps(
                            {
                                "type": "intent",
                                "content": intent_text,
                                "route": intent_route,
                            },
                            ensure_ascii=False,
                        )
                        yield f"data: {intent_data}\n\n"

                # 1. 构造简单节点日志
                log_message = ""
                if node_name == "weather_expert":
                    log_message = "🌤️ 天气数据获取完毕..."
                elif node_name == "rss_expert":
                    log_message = "📰 RSS 订阅源抓取完毕..."
                elif node_name == "doc_expert":
                    log_message = "📰 文档节点执行完毕，正在整理重试日志和结果..."
                elif node_name == "aggregator":
                    log_message = "✍️ 正在生成最终简报..."

                if log_message:
                    data = json.dumps(
                        {
                            "type": "log",
                            "message": log_message,
                            "node": node_name,
                        },
                        ensure_ascii=False,
                    )
                    yield f"data: {data}\n\n"
                    await asyncio.sleep(0.2)

                # 2. 如果是 doc_expert，推送详细的重试状态和日志
                if node_name == "doc_expert":
                    # node_status 事件（用于显示重试次数/最终状态）
                    status_payload = json.dumps(
                        {
                            "type": "node_status",
                            "node": "doc_expert",
                            "status": state.get("doc_status", ""),
                            "retry_count": state.get("doc_retry_count", 0),
                            "last_error": state.get("doc_last_error", ""),
                        },
                        ensure_ascii=False,
                    )
                    yield f"data: {status_payload}\n\n"
                    await asyncio.sleep(0.1)

                    # 逐条把 doc_logs 作为 log 事件发给前端
                    doc_logs = state.get("doc_logs") or []
                    for log_line in doc_logs:
                        line_payload = json.dumps(
                            {
                                "type": "log",
                                "node": "doc_expert",
                                "message": log_line,
                            },
                            ensure_ascii=False,
                        )
                        yield f"data: {line_payload}\n\n"
                        await asyncio.sleep(0.05)

        # 3. 这里的 state 是最后一次循环的 state，包含了最终结果
        # 注意：aggregator_node 的输出包含 messages，最后一条通常是结果
        final_message = state["messages"][-1].content
        # 4. 发送最终结果
        final_data = json.dumps(
            {
                "type": "result",
                "content": final_message,
            },
            ensure_ascii=False,
        )
        yield f"result: {final_message}\n\n"

    except Exception as e:
        logger.error(f"Error during streaming: {e}")
        error_data = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
        yield f"data: {error_data}\n\n"

@app_server.get("/")
def health_check():
    return {"status": "running"}

@app_server.post("/run-task", response_model=TaskResponse)
async def run_agent_task(request: TriggerRequest):
    logger.info(f"收到请求 user_id={request.user_id}, user_input={request.user_input}")
    user_input = request.user_input or "开始执行任务"
    inputs = {
        "messages": [("user", user_input)],
        "rss_data": [],
        "doc": "",
        "weather_report": "",
        "user_input": user_input,
        "user_intent": ""
    }
    
    # 返回流式响应，这样前端就能一点点收到数据了
    return StreamingResponse(
        event_generator(inputs), 
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    # 启动服务，监听 8000 端口
    print("🟢 服务启动中... 请关注此窗口的日志输出")
    uvicorn.run(app_server, host="0.0.0.0", port=8000)