import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI # pyright: ignore[reportMissingImports]
from .tools import ALL_TOOLS  # 导入刚才定义的工具

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
# 以后节点里直接用这个 model_with_tools
model_with_tools = _llm.bind_tools(ALL_TOOLS)