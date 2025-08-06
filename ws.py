# -*- coding: utf-8 -*-
"""
@Author: Junfeng Gao
@Date: 2025/8/4 10:43
@File: ws.py
@Description: 
"""
import websocket
import json
import threading
import time

SERVER_URL = "ws://47.100.81.66:8000/xiaozhi/v1/"  # 替换为你的服务器地址

HEADERS = {
    "Authorization": "Bearer xxx",
    "Protocol-Version": "1",
    "Device-Id": "AA:BB:CC:DD:EE:FF",
    "Client-Id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}

HELLO_MESSAGE = {
    "type": "hello",
    "version": 1,
    "features": {"mcp": True},
    "transport": "websocket",
    "audio_params": {
        "format": "opus",
        "sample_rate": 16000,
        "channels": 1,
        "frame_duration": 60
    }
}

def on_message(ws, message):
    if isinstance(message, bytes):
        print(f"[Binary] Received {len(message)} bytes")
        # 可用于解码或处理 binary 帧
    else:
        print(f"[Text] Received: {message}")
        try:
            msg = json.loads(message)
            if msg.get("type") == "hello":
                print("✅ 服务器 hello 收到，连接就绪")
        except Exception as e:
            print("❌ JSON 解析失败", e)

def on_open(ws):
    print("🔗 WebSocket connected")
    ws.send(json.dumps(HELLO_MESSAGE))
    print("📤 Sent hello")

def on_error(ws, error):
    print("❌ Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("❎ WebSocket closed")

def run():
    ws = websocket.WebSocketApp(
        SERVER_URL,
        header=[f"{k}: {v}" for k, v in HEADERS.items()],
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()

if __name__ == "__main__":
    threading.Thread(target=run).start()
