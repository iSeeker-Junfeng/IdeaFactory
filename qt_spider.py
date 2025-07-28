# -*- coding: utf-8 -*-
"""
@Author: Junfeng Gao
@Date: 2025/7/28 10:25
@File: qt_spider.py
@Description: 
"""
# -*- coding: utf-8 -*-
import sys
import os
import threading
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton,
    QListWidget, QMessageBox, QLabel
)

class VideoDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("X 视频下载器")
        self.setGeometry(100, 100, 500, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.input_label = QLabel("请输入视频链接：")
        layout.addWidget(self.input_label)

        self.url_input = QLineEdit()
        layout.addWidget(self.url_input)

        self.download_button = QPushButton("开始下载")
        self.download_button.clicked.connect(self.on_download)
        layout.addWidget(self.download_button)

        self.video_list = QListWidget()
        layout.addWidget(self.video_list)

        self.setLayout(layout)

    def on_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入有效的视频地址")
            return

        self.download_button.setEnabled(False)
        threading.Thread(target=self.download_video_multithreaded, args=(url,), daemon=True).start()

    def get_video_info(self, x_url):
        vid = x_url.split('/')[-1]
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        }
        down_load_url = 'https://download-x-video.com/api/parse'
        data = {"url": f"AMAZlNGNATURE/status/{vid}"}
        res = requests.post(url=down_load_url, headers=headers, json=data)
        if res.status_code != 200:
            return None
        video_url = res.json()['videoInfos'][2]['url']
        return video_url

    def get_file_size(self, url, headers):
        res = requests.head(url, headers=headers)
        return int(res.headers.get('Content-Length', 0))

    def download_chunk(self, url, start, end, part_num, headers):
        headers = headers.copy()
        headers['Range'] = f'bytes={start}-{end}'
        response = requests.get(url, headers=headers)
        with open(f'part_{part_num}.mp4', 'wb') as f:
            f.write(response.content)

    def merge_parts(self, total_parts, output_file):
        with open(output_file, 'wb') as outfile:
            for i in range(total_parts):
                with open(f'part_{i}.mp4', 'rb') as pf:
                    outfile.write(pf.read())
                os.remove(f'part_{i}.mp4')

    def download_video_multithreaded(self, x_url, thread_count=4):
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        }
        try:
            video_url = self.get_video_info(x_url)
            if not video_url:
                raise Exception("无法获取视频链接")

            total_size = self.get_file_size(video_url, headers)
            chunk_size = total_size // thread_count
            threads = []

            for i in range(thread_count):
                start = i * chunk_size
                end = total_size - 1 if i == thread_count - 1 else (start + chunk_size - 1)
                t = threading.Thread(target=self.download_chunk, args=(video_url, start, end, i, headers))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            filename = f"video_{len(os.listdir('.'))}.mp4"
            self.merge_parts(thread_count, filename)

            self.video_list.addItem(filename)
            QMessageBox.information(self, "完成", f"视频下载完成：{filename}")
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
        finally:
            self.download_button.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VideoDownloader()
    window.show()
    sys.exit(app.exec_())
