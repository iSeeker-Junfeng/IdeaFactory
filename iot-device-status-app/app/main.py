from fastapi import FastAPI, WebSocket, Query
import uvicorn
import asyncio
import json
import os

from starlette.responses import HTMLResponse

from sim_api import app as sim_api_app, test_functions

# 创建FastAPI应用
app = FastAPI()

# 挂载静态文件目录（如果有的话）
# app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册sim_api路由
app.include_router(sim_api_app.router, prefix="/api")

# 存储WebSocket连接
connected_clients = set()

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化操作"""
    print("应用正在启动...")
    # 可以在这里添加任何需要在应用启动时执行的代码

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理操作"""
    print("应用正在关闭...")
    # 可以在这里添加任何需要在应用关闭时执行的代码

@app.get("/")
async def read_root():
    """返回前端HTML页面"""
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建test_ui.html的绝对路径
    html_path = os.path.join(current_dir, "test_ui.html")
    
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.websocket("/ws/test-results")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，用于实时测试结果推送"""
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            # 接收客户端消息（可选）
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get('type') == 'get_functions':
                # 当客户端请求函数列表时发送
                await websocket.send_json({
                    "type": "function_list",
                    "functions": list(test_functions.keys())
                })
            
    except Exception as e:
        print(f"WebSocket连接异常: {e}")
    finally:
        connected_clients.remove(websocket)

async def broadcast_test_start(function_name: str):
    """广播测试开始事件给所有连接的客户端"""
    if connected_clients:
        message = {
            "type": "test_start",
            "functionName": function_name
        }
        await asyncio.gather(
            *[client.send_json(message) for client in connected_clients]
        )

async def broadcast_test_result(function_name: str, result: dict):
    """广播测试结果给所有连接的客户端"""
    if connected_clients:
        message = {
            "type": "test_result",
            "functionName": function_name,
            "result": result
        }
        await asyncio.gather(
            *[client.send_json(message) for client in connected_clients]
        )

@app.post("/run-test")
async def run_test(function_name: str):
    """API端点：运行指定名称的测试函数并返回结果"""
    if function_name not in test_functions:
        return {"error": f"函数 {function_name} 未找到"}
    
    try:
        # 广播测试开始事件
        asyncio.create_task(broadcast_test_start(function_name))
        
        # 运行测试函数
        result = await test_functions[function_name]()
        
        # 广播测试结果
        asyncio.create_task(broadcast_test_result(function_name, result))
        
        return result
    except Exception as e:
        error_result = {
            "error": f"执行函数 {function_name} 时发生错误: {str(e)}",
            "result": "错误"
        }
        asyncio.create_task(broadcast_test_result(function_name, error_result))
        return error_result

@app.get("/run-test")
async def run_test_get(function_name: str = Query(..., description="要运行的测试函数名称")):
    """GET端点：运行指定名称的测试函数并返回结果"""
    if function_name not in test_functions:
        return {"error": f"函数 {function_name} 未找到"}
    
    try:
        # 广播测试开始事件
        asyncio.create_task(broadcast_test_start(function_name))
        
        # 运行测试函数
        result = await test_functions[function_name]()
        
        # 广播测试结果
        asyncio.create_task(broadcast_test_result(function_name, result))
        
        return result
    except Exception as e:
        error_result = {
            "error": f"执行函数 {function_name} 时发生错误: {str(e)}",
            "result": "错误"
        }
        asyncio.create_task(broadcast_test_result(function_name, error_result))
        return error_result

if __name__ == "__main__":
    # 启动应用
    uvicorn.run(app, host="0.0.0.0", port=8000)