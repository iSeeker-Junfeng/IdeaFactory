# -*- coding: utf-8 -*-
"""
@Author: Junfeng Gao
@Date: 2025/7/14 9:28
@File: proxyServer.py
@Description: 
"""
import socket
import threading
import select

# 监听地址与端口
LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 9001
BUFFER_SIZE = 65536
TIMEOUT = 60  # s

def relay(src, dst):
    """双向转发字节流，直到任意一端关闭"""
    try:
        while True:
            r, _, _ = select.select([src, dst], [], [], TIMEOUT)
            if not r:
                break
            for s in r:
                data = s.recv(BUFFER_SIZE)
                if not data:
                    return
                (dst if s is src else src).sendall(data)
    finally:
        src.close()
        dst.close()

def handle_client(client_sock, addr):
    client_sock.settimeout(TIMEOUT)
    try:
        # 读取首行
        request_line = b''
        while not request_line.endswith(b'\r\n'):
            chunk = client_sock.recv(1)
            if not chunk:
                return
            request_line += chunk
        method, url, version = request_line.decode().strip().split()
        print(method, url, version)
        # 读取并丢弃剩余请求头
        headers = b''
        while b'\r\n\r\n' not in headers:
            headers += client_sock.recv(BUFFER_SIZE)

        if method.upper() == 'CONNECT':
            host, port = url.split(':')
            port = int(port)
            with socket.create_connection((host, port), timeout=TIMEOUT) as remote:
                client_sock.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
                relay(client_sock, remote)
        else:
            # 普通 HTTP：url 可能是绝对 URI，也可能是 /path
            from urllib.parse import urlsplit
            parsed = urlsplit(url)
            host = parsed.hostname or next((h for h in headers.decode().split('\r\n') if h.lower().startswith('host:')), '').split(':', 1)[-1].strip()
            port = parsed.port or 80
            path = parsed.path or '/'
            if parsed.query:
                path += '?' + parsed.query

            with socket.create_connection((host, port), timeout=TIMEOUT) as remote:
                # 重新组装首行，去掉绝对 URI
                remote.sendall(f'{method} {path} {version}\r\n'.encode() + headers)
                relay(client_sock, remote)
    except Exception as e:
        print(f'[{addr}] error:', e)
    finally:
        client_sock.close()

def start_proxy():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((LISTEN_HOST, LISTEN_PORT))
        server.listen()
        print(f'[*] Tiny proxy listening on {LISTEN_HOST}:{LISTEN_PORT}')
        while True:
            client, addr = server.accept()
            threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()

if __name__ == '__main__':
    start_proxy()
