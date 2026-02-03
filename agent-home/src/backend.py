# src/backend.py
import os
import uvicorn
import logging
import json
import asyncio
import urllib3
import langchain
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# 定义请求数据模型 (这里暂时为空，未来可以传 prompt)
class TriggerRequest(BaseModel):
    user_id: str = "default_user"

# 定义响应数据模型
class TaskResponse(BaseModel):
    result: str
    details: str = ""

async def event_generator(inputs):
    """
    这是一个生成器，负责监听 LangGraph 的运行步骤，
    并把每一步的状态实时推送到前端。
    """
    try:
        # 使用 astream (异步流) 代替 invoke
        # 这样每当一个 Node 运行完，我们就能收到通知
        async for event in graph.astream(inputs):
            for node_name, state in event.items():
                # 1. 构造日志消息
                log_message = ""
                if node_name == "weather_node":
                    log_message = "🌤️ 天气数据获取完毕..."
                elif node_name == "rss_agent_node":
                    log_message = "📰 RSS 订阅源抓取完毕..."
                elif node_name == "aggregator_node":
                    log_message = "✍️ 正在生成最终简报..."
                
                # 2. 发送 SSE 格式的数据包 (步骤日志)
                if log_message:
                    data = json.dumps({
                        "type": "log", 
                        "message": log_message,
                        "node": node_name
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    # 稍微模拟一下思考停顿，让用户看清日志 (可选)
                    await asyncio.sleep(0.5)

        # 3. 这里的 state 是最后一次循环的 state，包含了最终结果
        # 注意：aggregator_node 的输出包含 messages，最后一条通常是结果
        final_message = state["messages"][-1].content
        # 4. 发送最终结果
        final_data = json.dumps({
            "type": "result", 
            "content": final_message
        }, ensure_ascii=False)
        yield f"data: {final_data}\n\n"

    except Exception as e:
        logger.error(f"Error during streaming: {e}")
        error_data = json.dumps({"type": "error", "message": str(e)})
        yield f"data: {error_data}\n\n"

@app_server.get("/")
def health_check():
    return {"status": "running"}

@app_server.post("/run-task", response_model=TaskResponse)
async def run_agent_task(request: TriggerRequest):
    logger.info(f"收到请求: {request.user_id}")
    inputs = {
        "messages": [("user", "开始执行任务")],
        "weather": "",
        "rss_data": []
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