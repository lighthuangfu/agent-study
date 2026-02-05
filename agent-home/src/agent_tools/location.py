import requests
from langchain_core.tools import tool
# 5. 原有的定位工具
@tool(description="Get the current city location based on IP address.")
def get_current_location():
    print(">>> [Location Tool] 正在获取当前城市信息...")
    """
    通过 IP 地址获取当前的城市名称。
    返回格式例如：Beijing, China 或 Shanghai
    """
    try:
        # 使用 ip-api.com 的免费接口
        response = requests.get('http://ip-api.com/json/?lang=zh-CN', timeout=5)
        data = response.json()
        if data['status'] == 'success':
            return f"{data['city']}, {data['country']}"
        else:
            return "Unknown Location"
    except Exception as e:
        return f"定位失败: {str(e)}"
