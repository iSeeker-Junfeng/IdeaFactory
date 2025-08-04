#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智服务器 Python 客户端
实时播放收集到的音频字节 - 修复版本
"""

import asyncio
import json
import logging
import random
import string
import time
import websockets
import requests
import subprocess
import tempfile
import os
import threading
from typing import Optional, Dict, Any
from collections import deque

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class XiaozhiClient:
    def __init__(self,
                 ws_url: str = "ws://127.0.0.1:8000/xiaozhi/v1/",
                 ota_url: str = "http://127.0.0.1:8002/xiaozhi/ota/",
                 device_mac: str = None,
                 client_id: str = "python_test_client",
                 token: str = "your-token1"):

        self.ws_url = ws_url
        self.ota_url = ota_url
        self.device_mac = device_mac or self._generate_random_mac()
        self.client_id = client_id
        self.token = token
        self.device_name = "Python测试设备"

        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.session_id: Optional[str] = None
        self.is_connected = False
        self.message_handlers = {}

        # 音频相关 - 流式播放
        self.audio_queue = deque()  # 音频数据队列
        self.is_receiving_audio = False
        self.ffplay_process = None
        self.audio_thread = None
        self.audio_lock = threading.Lock()
        self.audio_buffer = bytearray()  # 累积音频数据
        self.last_audio_time = 0

        # 注册消息处理器
        self._register_handlers()

    def _generate_random_mac(self) -> str:
        """生成随机MAC地址"""
        hex_digits = '0123456789ABCDEF'
        mac_parts = []
        for i in range(6):
            part = ''.join(random.choice(hex_digits) for _ in range(2))
            mac_parts.append(part)
        return ':'.join(mac_parts)

    def _register_handlers(self):
        """注册消息处理器"""
        self.message_handlers = {
            'hello': self._handle_hello,
            'tts': self._handle_tts,
            'stt': self._handle_stt,
            'llm': self._handle_llm,
            'mcp': self._handle_mcp,
            'audio': self._handle_audio
        }

    async def check_ota(self) -> bool:
        """检查OTA状态"""
        try:
            headers = {
                'Content-Type': 'application/json',
                'Device-Id': self.device_mac,
                'Client-Id': self.client_id
            }

            body = {
                "version": 0,
                "uuid": "",
                "application": {
                    "name": "xiaozhi-python-test",
                    "version": "1.0.0",
                    "compile_time": "2025-04-16 10:00:00",
                    "idf_version": "4.4.3",
                    "elf_sha256": "1234567890abcdef1234567890abcdef1234567890abcdef"
                },
                "ota": {
                    "label": "xiaozhi-python-test",
                },
                "board": {
                    "type": "xiaozhi-python-test",
                    "ssid": "xiaozhi-python-test",
                    "rssi": 0,
                    "channel": 0,
                    "ip": "192.168.1.1",
                    "mac": self.device_mac
                },
                "flash_size": 0,
                "minimum_free_heap_size": 0,
                "mac_address": self.device_mac,
                "chip_model_name": "",
                "chip_info": {
                    "model": 0,
                    "cores": 0,
                    "revision": 0,
                    "features": 0
                },
                "partition_table": [
                    {
                        "label": "",
                        "type": 0,
                        "subtype": 0,
                        "address": 0,
                        "size": 0
                    }
                ]
            }

            response = requests.post(self.ota_url, headers=headers, json=body)
            if response.ok:
                result = response.json()
                logger.info(f"OTA检查成功: {result}")
                return True
            else:
                logger.error(f"OTA检查失败: {response.status_code} {response.text}")
                return False

        except Exception as e:
            logger.error(f"OTA检查错误: {e}")
            return False

    async def connect(self) -> bool:
        """连接到WebSocket服务器"""
        try:
            # 先检查OTA
            logger.info("检查OTA状态...")
            ota_ok = await self.check_ota()
            if not ota_ok:
                logger.warning("OTA检查失败，但继续尝试连接...")

            # 构建WebSocket URL
            ws_url_with_params = f"{self.ws_url}?device-id={self.device_mac}&client-id={self.client_id}"
            logger.info(f"连接到: {ws_url_with_params}")

            # 建立WebSocket连接
            self.websocket = await websockets.connect(ws_url_with_params)
            self.is_connected = True
            logger.info("WebSocket连接成功")

            # 发送hello消息
            await self.send_hello()

            return True

        except Exception as e:
            logger.error(f"连接失败: {e}")
            self.is_connected = False
            return False

    async def send_hello(self):
        """发送hello握手消息"""
        if not self.websocket:
            return

        hello_message = {
            "type": "hello",
            "device_id": self.device_mac,
            "device_name": self.device_name,
            "device_mac": self.device_mac,
            "token": self.token,
            "features": {
                "mcp": True
            }
        }

        await self.send_message(hello_message)
        logger.info("已发送hello消息")

    async def send_message(self, message: Dict[str, Any]):
        """发送消息"""
        if not self.websocket:
            logger.error("WebSocket未连接")
            return

        try:
            message_str = json.dumps(message, ensure_ascii=False)
            await self.websocket.send(message_str)
            logger.debug(f"发送消息: {message_str}")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    async def send_text_message(self, text: str):
        """发送文本消息"""
        message = {
            "type": "listen",
            "mode": "manual",
            "state": "detect",
            "text": text
        }
        await self.send_message(message)
        logger.info(f"发送文本消息: {text}")

    async def start_listening(self):
        """开始监听模式"""
        message = {
            "type": "listen",
            "mode": "manual",
            "state": "start"
        }
        await self.send_message(message)
        logger.info("开始监听模式")

    async def stop_listening(self):
        """停止监听模式"""
        message = {
            "type": "listen",
            "mode": "manual",
            "state": "stop"
        }
        await self.send_message(message)
        logger.info("停止监听模式")

    async def handle_message(self, message_data):
        """处理接收到的消息 - 支持文本和二进制数据"""
        try:
            # 检查是否为文本消息
            if isinstance(message_data, str):
                # 文本消息，尝试解析JSON
                message = json.loads(message_data)
                msg_type = message.get('type')

                if msg_type in self.message_handlers:
                    await self.message_handlers[msg_type](message)
                else:
                    logger.info(f"未知消息类型: {msg_type}, 内容: {message}")

            else:
                # 二进制数据（音频数据）
                await self._handle_binary_data(message_data)

        except json.JSONDecodeError:
            logger.warning(f"收到非JSON文本消息: {message_data}")
        except Exception as e:
            logger.error(f"处理消息错误: {e}")

    async def _handle_binary_data(self, binary_data):
        """处理二进制音频数据 - 累积播放"""
        try:
            data_size = len(binary_data)

            if data_size == 0:
                logger.info("收到空音频帧，音频传输结束")
                await self._play_accumulated_audio()
            else:
                logger.info(f"收到音频数据，大小: {data_size} 字节")

                # 将音频数据累积到缓冲区
                with self.audio_lock:
                    self.audio_buffer.extend(binary_data)
                    self.last_audio_time = time.time()

        except Exception as e:
            logger.error(f"处理二进制数据错误: {e}")

    async def _play_accumulated_audio(self):
        """播放累积的音频数据"""
        try:
            with self.audio_lock:
                if len(self.audio_buffer) == 0:
                    logger.info("没有音频数据需要播放")
                    return

                # 创建临时文件
                temp_fd, temp_path = tempfile.mkstemp(suffix='.opus')
                os.close(temp_fd)

                # 将累积的音频数据写入文件
                with open(temp_path, 'wb') as f:
                    f.write(self.audio_buffer)

                total_size = len(self.audio_buffer)
                logger.info(f"准备播放音频，总大小: {total_size} 字节，文件: {temp_path}")

                # 清空缓冲区
                self.audio_buffer.clear()

            # 启动ffplay播放音频文件
            await self._play_audio_file(temp_path)

        except Exception as e:
            logger.error(f"播放累积音频失败: {e}")

    async def _play_audio_file(self, audio_file_path):
        """播放音频文件"""
        try:
            # 启动ffplay进程播放音频文件
            process = subprocess.Popen([
                'ffplay', '-nodisp', '-autoexit', '-f', 'opus',
                '-ar', '16000', '-ac', '1', audio_file_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            logger.info(f"开始播放音频文件: {audio_file_path}")

            # 等待播放完成
            try:
                process.wait(timeout=30)  # 最多等待30秒
                logger.info("音频播放完成")
            except subprocess.TimeoutExpired:
                logger.warning("音频播放超时，强制终止")
                process.terminate()
            except Exception as e:
                logger.error(f"等待音频播放失败: {e}")

            # 删除临时文件
            try:
                os.remove(audio_file_path)
                logger.debug(f"已删除临时文件: {audio_file_path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败: {e}")

        except Exception as e:
            logger.error(f"播放音频文件失败: {e}")

    async def _handle_hello(self, message: Dict[str, Any]):
        """处理hello响应"""
        self.session_id = message.get('session_id')
        logger.info(f"收到hello响应，会话ID: {self.session_id}")

    async def _handle_tts(self, message: Dict[str, Any]):
        """处理TTS消息"""
        state = message.get('state')
        text = message.get('text', '')

        if state == 'start':
            logger.info("服务器开始发送语音")
        elif state == 'sentence_start':
            logger.info(f"语音段开始: {text}")
        elif state == 'sentence_end':
            logger.info(f"语音段结束: {text}")
        elif state == 'stop':
            logger.info("服务器语音传输结束")
            # 播放累积的音频
            await self._play_accumulated_audio()
        else:
            logger.info(f"TTS状态: {state}, 文本: {text}")

    async def _handle_stt(self, message: Dict[str, Any]):
        """处理语音识别结果"""
        text = message.get('text', '')
        logger.info(f"语音识别结果: {text}")

    async def _handle_llm(self, message: Dict[str, Any]):
        """处理大模型回复"""
        text = message.get('text', '')
        if text and text != '😊':
            logger.info(f"大模型回复: {text}")

    async def _handle_mcp(self, message: Dict[str, Any]):
        """处理MCP消息"""
        payload = message.get('payload', {})
        method = payload.get('method')

        logger.info(f"收到MCP消息: {method}")

        # 模拟客户端响应
        if method == 'tools/list':
            response = {
                "session_id": self.session_id or "",
                "type": "mcp",
                "payload": {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "result": {
                        "tools": [
                            {
                                "name": "self.get_device_status",
                                "description": "Provides the real-time information of the device...",
                                "inputSchema": {"type": "object", "properties": {}}
                            },
                            {
                                "name": "self.audio_speaker.set_volume",
                                "description": "Set the volume of the audio speaker...",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"volume": {"type": "integer", "minimum": 0, "maximum": 100}},
                                    "required": ["volume"]
                                }
                            }
                        ]
                    }
                }
            }
            await self.send_message(response)
            logger.info("已回复tools/list")

        elif method == 'tools/call':
            msg_id = payload.get('id')
            response = {
                "session_id": self.session_id or "",
                "type": "mcp",
                "payload": {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [{"type": "text", "text": "true"}],
                        "isError": False
                    }
                }
            }
            await self.send_message(response)
            logger.info("已回复tools/call")

    async def _handle_audio(self, message: Dict[str, Any]):
        """处理音频消息"""
        logger.info(f"收到音频消息: {message}")

    async def listen_for_messages(self):
        """监听消息循环 - 保持连接"""
        if not self.websocket:
            logger.error("WebSocket未连接")
            return

        try:
            async for message in self.websocket:
                await self.handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket连接已关闭")
            self.is_connected = False
        except Exception as e:
            logger.error(f"监听消息错误: {e}")
            self.is_connected = False

    async def disconnect(self):
        """断开连接"""
        # 播放剩余的音频数据
        await self._play_accumulated_audio()

        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("已断开连接")

    async def run_interactive(self):
        """运行交互式客户端 - 保持连接"""
        # 连接服务器
        if not await self.connect():
            return

        # 启动消息监听任务 - 在后台保持连接
        listen_task = asyncio.create_task(self.listen_for_messages())

        try:
            logger.info("客户端已启动，输入消息发送给服务器（输入 'quit' 退出）")

            while self.is_connected:
                try:
                    # 等待用户输入
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None, input, "> "
                    )

                    if user_input.lower() == 'quit':
                        break
                    elif user_input.lower() == 'start':
                        await self.start_listening()
                    elif user_input.lower() == 'stop':
                        await self.stop_listening()
                    elif user_input.strip():
                        await self.send_text_message(user_input)

                except KeyboardInterrupt:
                    break
                except EOFError:
                    break

        finally:
            # 清理
            listen_task.cancel()
            await self.disconnect()


async def main():
    """主函数"""
    # 创建客户端
    client = XiaozhiClient(
        ws_url="wss://2662r3426b.vicp.fun/xiaozhi/v1/",
        ota_url="https://2662r3426b.vicp.fun/xiaozhi/ota/",
        device_mac="AA:BB:CC:DD:EE:FF",  # 可以修改为你的设备MAC
        client_id="python_test_client",
        token="your-token1"
    )

    # 运行交互式客户端
    await client.run_interactive()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序错误: {e}")