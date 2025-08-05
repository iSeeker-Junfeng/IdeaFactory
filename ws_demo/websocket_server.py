import asyncio
import websockets
import json
import logging
from typing import Set, Dict
import time
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioWebSocketServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.sender_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.receiver_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.clients_info: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.start_time = time.time()
    
    async def register_client(self, websocket, path):
        """注册客户端连接"""
        try:
            print(f"新客户端连接: {websocket.remote_address}")
            
            # 等待客户端发送身份信息
            message = await websocket.recv()
            print(f"收到客户端消息: {message[:100]}...")  # 只显示前100个字符
            
            data = json.loads(message)
            client_type = data.get('type')
            client_id = data.get('id', str(id(websocket)))
            
            self.clients_info[websocket] = client_type
            
            if client_type == 'sender':
                self.sender_clients.add(websocket)
                logger.info(f"发送客户端 {client_id} 已连接")
                print(f"✓ 发送客户端 {client_id} 已连接")
            elif client_type == 'receiver':
                self.receiver_clients.add(websocket)
                logger.info(f"接收客户端 {client_id} 已连接")
                print(f"✓ 接收客户端 {client_id} 已连接")
            else:
                logger.warning(f"未知客户端类型: {client_type}")
                print(f"⚠ 未知客户端类型: {client_type}")
                return
            
            # 发送确认消息
            ack_message = {
                'type': 'connection_ack',
                'status': 'connected',
                'client_type': client_type
            }
            await websocket.send(json.dumps(ack_message))
            print(f"已发送确认消息给 {client_type} 客户端")
            
            self.print_status()
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            print(f"✗ JSON解析错误: {e}")
            return
        except Exception as e:
            logger.error(f"注册客户端时出错: {e}")
            print(f"✗ 注册客户端失败: {e}")
            print(f"错误详情: {traceback.format_exc()}")
            return
    
    def print_status(self):
        """打印当前状态"""
        uptime = int(time.time() - self.start_time)
        print(f"\n=== 服务器状态 ===")
        print(f"运行时间: {uptime} 秒")
        print(f"发送端连接数: {len(self.sender_clients)}")
        print(f"接收端连接数: {len(self.receiver_clients)}")
        print(f"总连接数: {len(self.sender_clients) + len(self.receiver_clients)}")
        print("=" * 20)
    
    async def handle_sender_message(self, websocket, message):
        """处理发送客户端的音频数据"""
        try:
            # 转发音频数据给所有接收客户端
            if self.receiver_clients:
                # 创建转发消息
                forward_message = {
                    'type': 'audio_data',
                    'data': message
                }
                
                # 发送给所有接收客户端
                disconnected_clients = set()
                for receiver in self.receiver_clients:
                    try:
                        await receiver.send(json.dumps(forward_message))
                    except websockets.exceptions.ConnectionClosed:
                        disconnected_clients.add(receiver)
                    except Exception as e:
                        logger.error(f"发送音频数据时出错: {e}")
                        disconnected_clients.add(receiver)
                
                # 清理断开的连接
                for client in disconnected_clients:
                    self.receiver_clients.discard(client)
                    self.clients_info.pop(client, None)
                    logger.info("接收客户端连接已断开")
                    print("⚠ 接收客户端连接已断开")
                
                # 只在有接收端时显示转发信息
                if len(self.receiver_clients) > 0:
                    print(f"\r音频数据已转发给 {len(self.receiver_clients)} 个接收客户端", end="", flush=True)
            else:
                print("\r等待接收客户端连接...", end="", flush=True)
                
        except Exception as e:
            logger.error(f"处理发送客户端消息时出错: {e}")
    
    async def handle_receiver_message(self, websocket, message):
        """处理接收客户端的消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'ready':
                logger.info("接收客户端准备就绪")
                print("✓ 接收客户端准备就绪")
            elif message_type == 'status':
                status = data.get('status')
                logger.info(f"接收客户端状态: {status}")
                print(f"接收客户端状态: {status}")
            else:
                logger.info(f"收到接收客户端消息: {message_type}")
                
        except Exception as e:
            logger.error(f"处理接收客户端消息时出错: {e}")
    
    async def handle_client(self, websocket):
        """处理客户端连接"""
        try:
            print(f"\n新连接: {websocket.remote_address}")
            
            # 先注册客户端
            await self.register_client(websocket, "")
            
            # 如果注册失败，直接返回
            if websocket not in self.clients_info:
                print("客户端注册失败，关闭连接")
                return
            
            # 处理客户端消息
            async for message in websocket:
                try:
                    # 检查客户端类型
                    client_type = self.clients_info.get(websocket)
                    
                    if client_type == 'sender':
                        await self.handle_sender_message(websocket, message)
                    elif client_type == 'receiver':
                        await self.handle_receiver_message(websocket, message)
                    else:
                        logger.warning(f"未知客户端类型: {client_type}")
                        
                except websockets.exceptions.ConnectionClosed:
                    print(f"客户端 {websocket.remote_address} 连接已关闭")
                    break
                except Exception as e:
                    logger.error(f"处理客户端消息时出错: {e}")
                    print(f"处理消息错误: {e}")
                    break
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("客户端连接已关闭")
            print(f"客户端 {websocket.remote_address} 连接已关闭")
        except Exception as e:
            logger.error(f"处理客户端连接时出错: {e}")
            print(f"连接处理错误: {e}")
            print(f"错误详情: {traceback.format_exc()}")
        finally:
            # 清理连接
            if websocket in self.sender_clients:
                self.sender_clients.discard(websocket)
                logger.info("发送客户端已断开")
                print("⚠ 发送客户端已断开")
            if websocket in self.receiver_clients:
                self.receiver_clients.discard(websocket)
                logger.info("接收客户端已断开")
                print("⚠ 接收客户端已断开")
            
            self.clients_info.pop(websocket, None)
            self.print_status()
    
    async def start(self):
        """启动WebSocket服务器"""
        logger.info(f"启动WebSocket服务器 {self.host}:{self.port}")
        print(f"=== WebSocket 音频服务器 ===")
        print(f"地址: {self.host}:{self.port}")
        print("正在启动服务器...")
        
        try:
            # 使用更简单的服务器启动方式
            server = await websockets.serve(
                self.handle_client, 
                self.host, 
                self.port,
                ping_interval=None,  # 禁用ping
                ping_timeout=None    # 禁用ping超时
            )
            
            print("✓ 服务器已启动，等待客户端连接...")
            print("按 Ctrl+C 停止服务器\n")
            logger.info("WebSocket服务器已启动，等待客户端连接...")
            
            # 保持服务器运行
            await server.wait_closed()
            
        except Exception as e:
            print(f"✗ 服务器启动失败: {e}")
            logger.error(f"服务器启动失败: {e}")

async def main():
    """主函数"""
    server = AudioWebSocketServer()
    await server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        logger.info("服务器已停止")
    except Exception as e:
        print(f"服务器运行错误: {e}")
        logger.error(f"服务器运行错误: {e}") 