import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI  # pyright: ignore[reportMissingImports]
from agent_tools.tools import ALL_TOOLS  # 导入刚才定义的工具
from agent.agent_builder import create_custom_agent

# 加载环境变量（幂等操作，多次调用安全）
# 如果 backend.py 已经调用过，这里不会重复加载
# 但如果 model.py 被单独导入（如测试），这里确保环境变量已加载
load_dotenv()

# 初始化基础模型
model = os.environ.get("DOUBAO_MODEL")
base_url = os.environ.get("DOUBAO_BASE_URL")
api_key = os.environ.get("DOUBAO_API_KEY")

print(f"🟢 获取到模型的名称是：{model}")
print(f"🟢 获取到模型的接入点：{base_url}")
print(f"🟢 获取到模型的API_KEY：{api_key}")

_llm = ChatOpenAI(
    model=model,
    base_url=base_url,
    api_key=api_key,
    temperature=0.1,
)

# 绑定工具，生成增强版模型
model_with_tools = _llm.bind_tools(ALL_TOOLS)