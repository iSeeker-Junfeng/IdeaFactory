import asyncio
import websockets
import json
import pyaudio
import wave
import threading
import time
import logging
from queue import Queue
import base64
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioSender:
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
        self.RECORD_SECONDS = 5
        
        # PyAudio实例
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.recording = False
        
        # 状态跟踪
        self.audio_sent_count = 0
        self.last_send_time = 0
    
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
                'type': 'sender',
                'id': 'audio_sender_001'
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
    
    def start_recording(self):
        """开始录音"""
        if self.recording:
            logger.warning("录音已在进行中")
            return
        
        try:
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            
            self.recording = True
            logger.info("开始录音...")
            print("✓ 开始录音...")
            
            # 在单独的线程中录音
            recording_thread = threading.Thread(target=self._record_audio)
            recording_thread.daemon = True
            recording_thread.start()
            
        except Exception as e:
            logger.error(f"启动录音时出错: {e}")
            print(f"✗ 启动录音失败: {e}")
    
    def stop_recording(self):
        """停止录音"""
        if not self.recording:
            logger.warning("没有在录音")
            return
        
        self.recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        logger.info("录音已停止")
        print("录音已停止")
    
    def _record_audio(self):
        """录音线程函数"""
        try:
            while self.recording:
                if self.stream and self.stream.is_active():
                    data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                    # 将音频数据放入队列
                    self.audio_queue.put(data)
                else:
                    break
        except Exception as e:
            logger.error(f"录音过程中出错: {e}")
    
    async def show_sending_status(self):
        """显示发送状态"""
        dots = 0
        while self.connected:
            status = "正在发送音频数据" + "." * (dots % 4)
            print(f"\r{status} (已发送 {self.audio_sent_count} 个数据包)", end="", flush=True)
            dots += 1
            await asyncio.sleep(2)
    
    async def send_audio_data(self):
        """发送音频数据到服务器"""
        print("开始发送音频数据...")
        
        # 启动状态显示
        status_task = asyncio.create_task(self.show_sending_status())
        
        while self.connected:
            try:
                # 从队列获取音频数据
                if not self.audio_queue.empty():
                    audio_data = self.audio_queue.get()
                    
                    # 将音频数据编码为base64
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    
                    # 发送到服务器
                    await self.websocket.send(audio_base64)
                    
                    # 更新统计信息
                    self.audio_sent_count += 1
                    self.last_send_time = time.time()
                    
                    # 控制发送频率，避免过于频繁
                    await asyncio.sleep(0.01)  # 10ms延迟
                else:
                    # 队列为空时短暂等待
                    await asyncio.sleep(0.001)
                    
            except websockets.exceptions.ConnectionClosed:
                logger.error("WebSocket连接已断开")
                self.connected = False
                print("\n⚠ WebSocket连接已断开")
                break
            except Exception as e:
                logger.error(f"发送音频数据时出错: {e}")
                print(f"\n发送错误: {e}")
                break
        
        # 取消状态显示任务
        if not status_task.done():
            status_task.cancel()
    
    async def run(self):
        """运行发送客户端"""
        try:
            print("=== 音频发送客户端 ===")
            print("正在启动...")
            
            # 连接到服务器
            if not await self.connect_to_server():
                print("连接失败，程序退出")
                return
            
            # 启动录音
            self.start_recording()
            
            print("\n客户端已准备就绪！")
            print("正在录制并发送音频...")
            print("按 Ctrl+C 停止\n")
            
            # 开始发送音频数据
            await self.send_audio_data()
            
        except Exception as e:
            logger.error(f"运行发送客户端时出错: {e}")
            print(f"✗ 运行错误: {e}")
            print(f"错误详情: {traceback.format_exc()}")
        finally:
            # 清理资源
            self.stop_recording()
            if self.websocket:
                await self.websocket.close()
            if self.p:
                self.p.terminate()
            logger.info("发送客户端已关闭")
            print(f"\n发送客户端已关闭 (总共发送了 {self.audio_sent_count} 个数据包)")

async def main():
    """主函数"""
    sender = AudioSender()
    
    try:
        await sender.run()
    except KeyboardInterrupt:
        print("\n正在停止发送客户端...")
        sender.stop_recording()

if __name__ == "__main__":
    asyncio.run(main()) 