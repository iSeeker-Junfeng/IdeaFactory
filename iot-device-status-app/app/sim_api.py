import json
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
import random
import requests

# 获取所有设备状态
def get_devices():
    response = requests.get('http://localhost:5000/api/devices')
    return response.json()

# 获取单个设备状态
def get_device(device_id):
    response = requests.get(f'http://localhost:5000/api/devices/{device_id}')
    return response.json()

class TestFunction:
    @staticmethod
    async def test_function_1() -> Dict[str, Any]:
        """模拟测试功能1，返回测试结果"""
        # 模拟测试耗时（5-10秒）
        duration = random.uniform(5, 10)
        await asyncio.sleep(duration)
        
        # 随机生成测试结果
        success = random.random() > 0.2  # 80%成功率
        return {
            "result": "success" if success else "failure",
            "duration": f"{duration:.2f}秒",
            "details": "测试功能1执行完成" if success else "测试功能1执行失败，请检查相关配置"
        }

# 测试函数映射表
test_functions = {
    "test_function_1": TestFunction.test_function_1
}

class FunctionCall:
    @staticmethod
    async def call_function(function_name: str) -> Dict[str, Any]:
        """调用指定名称的测试函数"""
        if function_name not in test_functions:
            return {
                "error": f"函数 {function_name} 未找到",
                "result": "错误"
            }
        
        try:
            # 使用eval执行函数调用
            result = await test_functions[function_name]()
            return result
        except Exception as e:
            return {
                "error": f"执行函数 {function_name} 时发生错误: {str(e)}",
                "result": "错误"
            }

# 创建FastAPI应用
app = FastAPI()

# 定义请求模型
class FunctionCallRequest(BaseModel):
    function_name: str

@app.post("/call-function")
async def call_function_endpoint(request: FunctionCallRequest):
    """API端点：接收函数调用请求"""
    result = await FunctionCall.call_function(request.function_name)
    return result

@app.get("/test-functions")
async def get_test_functions():
    """API端点：获取所有可用测试函数"""
    return {"functions": list(test_functions.keys())}