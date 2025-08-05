import asyncio
import websockets
import json
import pyaudio
import threading
import logging
from queue import Queue
import base64
import time
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioReceiver:
    def __init__(self, server_url='ws://localhost:8765'):
        self.server_url = server_url
        self.websocket = None
        self.connected = False
        self.audio_queue = Queue()
        
        # 音频配置
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        
        # PyAudio实例
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.playing = False
        
        # 状态跟踪
        self.audio_received = False
        self.last_audio_time = 0
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
    
    async def connect_to_server(self):
        """连接到WebSocket服务器"""
        try:
            print("正在连接到WebSocket服务器...")
            print(f"服务器地址: {self.server_url}")
            
            # 设置连接超时
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.server_url),
                timeout=10.0
            )
            
            print("✓ WebSocket连接已建立")
            
            # 发送身份信息
            identity = {
                'type': 'receiver',
                'id': 'audio_receiver_001'
            }
            identity_json = json.dumps(identity)
            print(f"发送身份信息: {identity_json}")
            
            await self.websocket.send(identity_json)
            
            # 等待服务器确认
            print("等待服务器确认...")
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
            print(f"收到服务器响应: {response}")
            
            data = json.loads(response)
            
            if data.get('type') == 'connection_ack' and data.get('status') == 'connected':
                self.connected = True
                logger.info("已连接到WebSocket服务器")
                print("✓ 已连接到服务器")
                
                # 发送准备就绪消息
                ready_message = {
                    'type': 'ready',
                    'status': 'ready_to_receive'
                }
                await self.websocket.send(json.dumps(ready_message))
                print("✓ 已发送准备就绪消息")
                
                return True
            else:
                logger.error("服务器连接失败")
                print("✗ 服务器连接失败")
                return False
                
        except asyncio.TimeoutError:
            logger.error("连接超时")
            print("✗ 连接超时，请检查服务器是否正在运行")
            return False
        except websockets.exceptions.InvalidURI:
            logger.error("无效的WebSocket URI")
            print("✗ 无效的WebSocket地址")
            return False
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"WebSocket连接已关闭: {e}")
            print(f"✗ WebSocket连接已关闭: {e}")
            return False
        except Exception as e:
            logger.error(f"连接服务器时出错: {e}")
            print(f"✗ 连接错误: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            return False
    
    def start_playing(self):
        """开始播放音频"""
        if self.playing:
            logger.warning("播放已在进行中")
            return
        
        try:
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                output=True,
                frames_per_buffer=self.CHUNK
            )
            
            self.playing = True
            logger.info("开始播放音频...")
            print("✓ 音频播放已启动")
            
            # 在单独的线程中播放
            playing_thread = threading.Thread(target=self._play_audio)
            playing_thread.daemon = True
            playing_thread.start()
            
        except Exception as e:
            logger.error(f"启动播放时出错: {e}")
            print(f"✗ 启动播放失败: {e}")
    
    def stop_playing(self):
        """停止播放音频"""
        if not self.playing:
            logger.warning("没有在播放")
            return
        
        self.playing = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        logger.info("播放已停止")
        print("音频播放已停止")
    
    def _play_audio(self):
        """播放音频线程函数"""
        try:
            while self.playing:
                if not self.audio_queue.empty():
                    audio_data = self.audio_queue.get()
                    if self.stream and self.stream.is_active():
                        self.stream.write(audio_data)
                else:
                    # 队列为空时短暂等待
                    time.sleep(0.001)
        except Exception as e:
            logger.error(f"播放音频过程中出错: {e}")
    
    async def show_waiting_status(self):
        """显示等待状态"""
        dots = 0
        while self.connected and not self.audio_received:
            status = "等待音频数据" + "." * (dots % 4)
            print(f"\r{status}", end="", flush=True)
            dots += 1
            await asyncio.sleep(1)
        
        if self.audio_received:
            print("\n✓ 开始接收音频数据")
    
    async def receive_audio_data(self):
        """接收音频数据"""
        print("正在等待发送客户端连接...")
        
        # 启动等待状态显示
        waiting_task = asyncio.create_task(self.show_waiting_status())
        
        while self.connected:
            try:
                # 接收服务器消息
                message = await asyncio.wait_for(self.websocket.recv(), timeout=30.0)
                
                try:
                    # 尝试解析为JSON消息
                    data = json.loads(message)
                    message_type = data.get('type')
                    
                    if message_type == 'audio_data':
                        # 解码音频数据
                        audio_base64 = data.get('data', '')
                        audio_data = base64.b64decode(audio_base64)
                        
                        # 将音频数据放入播放队列
                        self.audio_queue.put(audio_data)
                        
                        # 标记已收到音频数据
                        if not self.audio_received:
                            self.audio_received = True
                            waiting_task.cancel()  # 取消等待状态显示
                        
                        self.last_audio_time = time.time()
                        logger.debug("收到音频数据")
                    else:
                        logger.info(f"收到消息: {message_type}")
                        
                except json.JSONDecodeError:
                    # 如果不是JSON，可能是直接的音频数据
                    try:
                        audio_data = base64.b64decode(message)
                        self.audio_queue.put(audio_data)
                        
                        # 标记已收到音频数据
                        if not self.audio_received:
                            self.audio_received = True
                            waiting_task.cancel()  # 取消等待状态显示
                        
                        self.last_audio_time = time.time()
                        logger.debug("收到直接音频数据")
                    except Exception as e:
                        logger.warning(f"无法解析消息: {e}")
                        
            except asyncio.TimeoutError:
                print("\r等待音频数据超时，继续等待...", end="", flush=True)
                continue
            except websockets.exceptions.ConnectionClosed:
                logger.error("WebSocket连接已断开")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"接收音频数据时出错: {e}")
                print(f"\n接收错误: {e}")
                break
        
        # 取消等待任务
        if not waiting_task.done():
            waiting_task.cancel()
    
    async def run(self):
        """运行接收客户端"""
        try:
            print("=== 音频接收客户端 ===")
            print("正在启动...")
            
            # 连接到服务器
            if not await self.connect_to_server():
                print("连接失败，程序退出")
                return
            
            # 启动播放
            self.start_playing()
            
            print("\n客户端已准备就绪！")
            print("等待发送客户端发送音频...")
            print("按 Ctrl+C 停止\n")
            
            # 开始接收音频数据
            await self.receive_audio_data()
            
        except Exception as e:
            logger.error(f"运行接收客户端时出错: {e}")
            print(f"✗ 运行错误: {e}")
            print(f"错误详情: {traceback.format_exc()}")
        finally:
            # 清理资源
            self.stop_playing()
            if self.websocket:
                await self.websocket.close()
            if self.p:
                self.p.terminate()
            logger.info("接收客户端已关闭")
            print("\n接收客户端已关闭")

async def main():
    """主函数"""
    receiver = AudioReceiver()
    
    try:
        await receiver.run()
    except KeyboardInterrupt:
        print("\n正在停止接收客户端...")
        receiver.stop_playing()

if __name__ == "__main__":
    asyncio.run(main()) 