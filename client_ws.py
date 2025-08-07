#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小智服务器 Python 客户端 - 实时流式播放版本
一边接收一边播放音频
"""

import asyncio
import json
import logging
import random
import string
import time
import websockets
import requests
from typing import Optional, Dict, Any, List

from IdeaFactory.opus_encoder_tulis import OpusEncoderUtils

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


import threading
import queue
import pyaudio
import subprocess
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


opus_encoder = OpusEncoderUtils(
            sample_rate=16000, channels=1, frame_size_ms=60
        )
class StreamingAudioPlayer:
    """实时流式音频播放器（使用 pyaudio 播放）"""

    def __init__(self):
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.stream = None
        self.pyaudio_instance = pyaudio.PyAudio()
        self.temp_dir = tempfile.mkdtemp(prefix="streaming_audio_")
        self.frame_counter = 0

        # 假设解码后为 mono/48000Hz/16bit
        self.channels = 1
        self.rate = 48000
        self.format = pyaudio.paInt16

    def start_streaming(self):
        """开始流式播放"""
        if self.is_playing:
            return

        self.is_playing = True
        self.stream = self.pyaudio_instance.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            output=True
        )
        self.player_thread = threading.Thread(target=self._streaming_worker, daemon=True)
        self.player_thread.start()
        logger.info("流式播放器已启动")

    def stop_streaming(self):
        """停止流式播放"""
        self.is_playing = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.pyaudio_instance.terminate()
        logger.info("流式播放器已停止")

    def add_audio_frame(self, audio_data: bytes):
        """添加音频帧到播放队列"""
        if not self.is_playing:
            self.start_streaming()

        self.audio_queue.put(audio_data)

    def _streaming_worker(self):
        """流式播放工作线程"""
        while self.is_playing:
            try:
                audio_data = self.audio_queue.get(timeout=1)
                pcm_data = self._decode_opus_to_pcm(audio_data)
                if pcm_data:
                    self.stream.write(pcm_data)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"流式播放错误: {e}")

    def _decode_opus_to_pcm(self, opus_data: bytes) -> bytes:
        """用ffmpeg把opus字节解码成pcm原始流"""
        try:
            # 用 subprocess 启动 ffmpeg 解码器，输入 Opus 数据，输出 PCM 原始流
            opus = opus_encoder.encode_pcm_to_opus(opus_data,True)[0]
            print(f"{opus=}")
            ffmpeg = subprocess.Popen(
                ["ffmpeg", "-i", "pipe:0", "-f", "s16le", "-acodec", "pcm_s16le", "-ac", str(self.channels), "-ar", str(self.rate), "pipe:1"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            pcm_data, _ = ffmpeg.communicate(input=opus, timeout=5)
            return pcm_data
        except Exception as e:
            logger.error(f"解码错误: {e}")
            return None


    def _play_frame(self, frame_file):
        """播放单个音频帧"""
        try:
            # 使用ffplay播放音频帧
            cmd = [
                'ffplay', '-nodisp', '-autoexit', '-f', 'opus',
                '-ar', '16000', '-ac', '1', frame_file
            ]

            self.player_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # 等待播放完成（最多等待1秒）
            try:
                self.player_process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.player_process.terminate()

        except Exception as e:
            logger.error(f"播放音频帧失败: {e}")


class XiaozhiClient:
    def __init__(self,
                 ws_url: str = "ws://127.0.0.1:8000/xiaozhi/v1/",
                 ota_url: str = "http://127.0.0.1:8002/xiaozhi/ota/",
                 device_mac: str = None,
                 client_id: str = "guition-jc8012p4a1",
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

        # 音频相关
        self.audio_player = StreamingAudioPlayer()
        self.is_receiving_audio = False
        self.audio_lock = threading.Lock()
        self.playback_mode = "streaming"  # streaming, buffered, save_only

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
                    "name": "guition-jc8012p4a1",
                    "version": "1.0.0",
                    "compile_time": "2025-04-16 10:00:00",
                    "idf_version": "4.4.3",
                    "elf_sha256": "1234567890abcdef1234567890abcdef1234567890abcdef"
                },
                "ota": {
                    "label": "guition-jc8012p4a1",
                },
                "board": {
                    "type": "guition-jc8012p4a1",
                    "ssid": "guition-jc8012p4a1",
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
                return  result['websocket']['url']
                # return True
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
            self.ws_url = ota_ok
            # 构建WebSocket URL
            ws_url_with_params = f"{self.ws_url}?device-id={self.device_mac}&client-id={self.client_id}"
            print(ws_url_with_params)
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
        """处理二进制音频数据 - 实时流式播放"""
        try:
            data_size = len(binary_data)

            if data_size == 0:
                logger.info("收到空音频帧，音频传输结束")
                self.is_receiving_audio = False
            else:
                logger.info(f"收到音频数据，大小: {data_size} 字节")
                self.is_receiving_audio = True

                # 根据播放模式处理音频
                if self.playback_mode == "streaming":
                    # 实时流式播放
                    self.audio_player.add_audio_frame(binary_data)
                elif self.playback_mode == "buffered":
                    # 缓冲播放（原有逻辑）
                    await self._handle_buffered_audio(binary_data)
                elif self.playback_mode == "save_only":
                    # 仅保存
                    await self._save_audio_frame(binary_data)

        except Exception as e:
            logger.error(f"处理二进制数据错误: {e}")

    async def _handle_buffered_audio(self, binary_data):
        """处理缓冲音频（原有逻辑）"""
        # 这里保留原有的缓冲播放逻辑
        pass

    async def _save_audio_frame(self, binary_data):
        """保存音频帧"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        frame_file = f"audio_frame_{timestamp}_{len(binary_data)}.opus"

        with open(frame_file, 'wb') as f:
            f.write(binary_data)

        logger.info(f"音频帧已保存: {frame_file}")

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
        # 停止流式播放
        self.audio_player.stop_streaming()

        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("已断开连接")

    def set_playback_mode(self, mode: str):
        """设置播放模式"""
        valid_modes = ["streaming", "buffered", "save_only"]
        if mode in valid_modes:
            self.playback_mode = mode
            logger.info(f"播放模式设置为: {mode}")
        else:
            logger.warning(f"无效的播放模式: {mode}，有效模式: {valid_modes}")

    async def run_interactive(self):
        """运行交互式客户端 - 保持连接"""
        # 连接服务器
        if not await self.connect():
            return

        # 启动消息监听任务 - 在后台保持连接
        listen_task = asyncio.create_task(self.listen_for_messages())

        try:
            logger.info("客户端已启动，输入消息发送给服务器")
            logger.info("特殊命令:")
            logger.info("  'quit' - 退出程序")
            logger.info("  'start' - 开始录音")
            logger.info("  'stop' - 停止录音")
            logger.info("  'stream' - 切换到流式播放模式")
            logger.info("  'buffer' - 切换到缓冲播放模式")
            logger.info("  'save' - 切换到仅保存模式")

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
                    elif user_input.lower() == 'stream':
                        self.set_playback_mode("streaming")
                    elif user_input.lower() == 'buffer':
                        self.set_playback_mode("buffered")
                    elif user_input.lower() == 'save':
                        self.set_playback_mode("save_only")
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
        ws_url="",
        # ws_url="wss://2662r3426b.vicp.fun/xiaozhi/v1/",
        ota_url="http://47.100.81.66:8002/xiaozhi/ota/",
        # ota_url="https://2662r3426b.vicp.fun/xiaozhi/ota/",
        # device_mac="AA:BB:CC:DD:EE:FF",  # 可以修改为你的设备MAC
        device_mac="9c:9e:6e:54:73:94",  # 可以修改为你的设备MAC
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