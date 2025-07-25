# -*- coding: utf-8 -*-
"""
@Author: Junfeng Gao
@Date: 2025/7/14 15:58
@File: x_spider.py
@Description: 
"""
import requests
import threading
import os

def get_video_info(x_url):
    vid = x_url.split('/')[-1]
    print(f"Video ID: {vid}")
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"}
    down_load_url = 'https://download-x-video.com/api/parse'
    data = {"url": f"AMAZlNGNATURE/status/{vid}"}
    res = requests.post(url=down_load_url, headers=headers, json=data)
    video_url = res.json()['videoInfos'][2]['url']
    return video_url

def get_file_size(url, headers):
    res = requests.head(url, headers=headers)
    return int(res.headers.get('Content-Length', 0))

def download_chunk(url, start, end, part_num, headers):
    headers = headers.copy()
    headers['Range'] = f'bytes={start}-{end}'
    print(f"Downloading part {part_num}: bytes={start}-{end}")
    response = requests.get(url, headers=headers)
    with open(f'part_{part_num}.mp4', 'wb') as f:
        f.write(response.content)

def merge_parts(total_parts, output_file):
    with open(output_file, 'wb') as outfile:
        for i in range(total_parts):
            part_file = f'part_{i}.mp4'
            with open(part_file, 'rb') as pf:
                outfile.write(pf.read())
            os.remove(part_file)

def download_video_multithreaded(x_url, thread_count=4):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }
    video_url = get_video_info(x_url)
    total_size = get_file_size(video_url, headers)
    print(f"Video size: {total_size / 1024 / 1024:.2f} MB")

    chunk_size = total_size // thread_count
    threads = []

    for i in range(thread_count):
        start = i * chunk_size
        end = total_size - 1 if i == thread_count - 1 else (start + chunk_size - 1)
        t = threading.Thread(target=download_chunk, args=(video_url, start, end, i, headers))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    merge_parts(thread_count, '1.mp4')
    print("Download complete!")

# 示例调用
# download_video_multithreaded("https://twitter.com/AMAZlNGNATURE/status/1798726550925111787", thread_count=4)


if __name__ == '__main__':
    x_url = 'https://x.com/AMAZlNGNATURE/status/1907951899489227188'
    download_video_multithreaded(x_url)
