# -*- coding: utf-8 -*-
"""
@Author: Junfeng Gao
@Date: 2025/8/5 14:35
@File: audio_debug_tool.py
@Description: 
"""
# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频调试工具 - 用于分析和修复Opus音频文件
"""

import os
import sys
import subprocess
import tempfile
import struct
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudioDebugTool:
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
        self.ffplay_available = self._check_ffplay()

    def _check_ffmpeg(self):
        """检查ffmpeg是否可用"""
        try:
            result = subprocess.run(['ffmpeg', '-version'],
                                    capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _check_ffplay(self):
        """检查ffplay是否可用"""
        try:
            result = subprocess.run(['ffplay', '-version'],
                                    capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def analyze_opus_file(self, file_path):
        """分析Opus文件"""
        logger.info(f"分析Opus文件: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return False

        file_size = os.path.getsize(file_path)
        logger.info(f"文件大小: {file_size} 字节")

        # 读取文件头
        with open(file_path, 'rb') as f:
            header = f.read(32)
            logger.info(f"文件头 (hex): {header.hex()}")

            # 检查是否为有效的Opus文件
            if len(header) >= 8:
                # 检查OggS标识
                if header[:4] == b'OggS':
                    logger.info("检测到Ogg容器格式")
                    return self._analyze_ogg_opus(file_path)
                else:
                    logger.info("检测到原始Opus数据")
                    return self._analyze_raw_opus(file_path)

        return False

    def _analyze_ogg_opus(self, file_path):
        """分析Ogg容器中的Opus文件"""
        logger.info("分析Ogg容器中的Opus数据...")

        if self.ffmpeg_available:
            # 使用ffmpeg获取详细信息
            try:
                cmd = [
                    'ffprobe', '-v', 'quiet', '-print_format', 'json',
                    '-show_format', '-show_streams', file_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    logger.info("ffprobe分析结果:")
                    logger.info(result.stdout)
                else:
                    logger.error(f"ffprobe分析失败: {result.stderr}")
            except Exception as e:
                logger.error(f"ffprobe分析出错: {e}")

        return True

    def _analyze_raw_opus(self, file_path):
        """分析原始Opus数据"""
        logger.info("分析原始Opus数据...")

        with open(file_path, 'rb') as f:
            data = f.read()

        logger.info(f"数据总长度: {len(data)} 字节")

        # 尝试检测Opus帧
        frame_count = 0
        offset = 0

        while offset < len(data):
            if offset + 1 >= len(data):
                break

            # 读取帧长度 (假设是2字节长度)
            try:
                frame_length = struct.unpack('<H', data[offset:offset + 2])[0]
                offset += 2

                if offset + frame_length <= len(data):
                    frame_data = data[offset:offset + frame_length]
                    logger.info(f"帧 {frame_count}: 长度={frame_length}, 数据={frame_data[:16].hex()}")
                    offset += frame_length
                    frame_count += 1
                else:
                    logger.warning(f"帧长度超出文件范围: {frame_length}")
                    break
            except struct.error:
                logger.warning(f"无法解析帧长度，偏移: {offset}")
                break

        logger.info(f"检测到 {frame_count} 个Opus帧")
        return frame_count > 0

    def convert_opus_to_wav(self, opus_file, output_wav=None):
        """将Opus文件转换为WAV格式"""
        if not self.ffmpeg_available:
            logger.error("ffmpeg不可用，无法转换")
            return None

        if output_wav is None:
            output_wav = opus_file.replace('.opus', '.wav')

        try:
            cmd = [
                'ffmpeg', '-i', opus_file,
                '-ar', '16000', '-ac', '1',  # 16kHz, 单声道
                '-y',  # 覆盖输出文件
                output_wav
            ]

            logger.info(f"转换命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info(f"转换成功: {output_wav}")
                return output_wav
            else:
                logger.error(f"转换失败: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"转换出错: {e}")
            return None

    def play_audio_file(self, file_path, format_type='auto'):
        """播放音频文件"""
        if not self.ffplay_available:
            logger.error("ffplay不可用，无法播放")
            return False

        try:
            if format_type == 'opus':
                cmd = ['ffplay', '-nodisp', '-autoexit', '-f', 'opus', '-ar', '16000', '-ac', '1', file_path]
            elif format_type == 'wav':
                cmd = ['ffplay', '-nodisp', '-autoexit', file_path]
            else:
                cmd = ['ffplay', '-nodisp', '-autoexit', file_path]

            logger.info(f"播放命令: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 等待播放完成
            process.wait(timeout=30)
            logger.info("播放完成")
            return True

        except subprocess.TimeoutExpired:
            logger.warning("播放超时")
            process.terminate()
            return False
        except Exception as e:
            logger.error(f"播放出错: {e}")
            return False

    def fix_opus_file(self, input_file, output_file=None):
        """修复Opus文件"""
        if output_file is None:
            output_file = input_file.replace('.opus', '_fixed.opus')

        logger.info(f"尝试修复Opus文件: {input_file} -> {output_file}")

        # 方法1: 使用ffmpeg重新编码
        if self.ffmpeg_available:
            try:
                cmd = [
                    'ffmpeg', '-i', input_file,
                    '-c:a', 'libopus', '-b:a', '16k', '-ar', '16000', '-ac', '1',
                    '-y', output_file
                ]

                logger.info(f"修复命令: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    logger.info(f"修复成功: {output_file}")
                    return output_file
                else:
                    logger.error(f"修复失败: {result.stderr}")
            except Exception as e:
                logger.error(f"修复出错: {e}")

        return None

    def create_test_opus(self, output_file="test_opus.opus"):
        """创建测试用的Opus文件"""
        if not self.ffmpeg_available:
            logger.error("ffmpeg不可用，无法创建测试文件")
            return None

        try:
            # 生成1秒的测试音频 (440Hz正弦波)
            cmd = [
                'ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                '-c:a', 'libopus', '-b:a', '16k', '-ar', '16000', '-ac', '1',
                '-y', output_file
            ]

            logger.info(f"创建测试文件命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info(f"测试文件创建成功: {output_file}")
                return output_file
            else:
                logger.error(f"创建测试文件失败: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"创建测试文件出错: {e}")
            return None

    def batch_process_directory(self, directory):
        """批量处理目录中的Opus文件"""
        directory = Path(directory)
        opus_files = list(directory.glob("*.opus"))

        logger.info(f"找到 {len(opus_files)} 个Opus文件")

        for opus_file in opus_files:
            logger.info(f"\n处理文件: {opus_file}")

            # 分析文件
            self.analyze_opus_file(str(opus_file))

            # 尝试转换
            wav_file = self.convert_opus_to_wav(str(opus_file))
            if wav_file:
                # 尝试播放
                self.play_audio_file(wav_file, 'wav')

                # 清理临时文件
                try:
                    os.remove(wav_file)
                except:
                    pass


def main():
    """主函数"""
    tool = AudioDebugTool()

    print("音频调试工具")
    print("=" * 50)
    print(f"ffmpeg可用: {tool.ffmpeg_available}")
    print(f"ffplay可用: {tool.ffplay_available}")
    print()

    if len(sys.argv) < 2:
        print("用法:")
        print("  python audio_debug_tool.py <opus文件>")
        print("  python audio_debug_tool.py --test")
        print("  python audio_debug_tool.py --batch <目录>")
        return

    if sys.argv[1] == "--test":
        # 创建测试文件
        test_file = tool.create_test_opus()
        if test_file:
            print(f"测试文件已创建: {test_file}")
            tool.analyze_opus_file(test_file)
            tool.play_audio_file(test_file, 'opus')
    elif sys.argv[1] == "--batch" and len(sys.argv) > 2:
        # 批量处理
        tool.batch_process_directory(sys.argv[2])
    else:
        # 分析单个文件
        opus_file = sys.argv[1]
        if tool.analyze_opus_file(opus_file):
            # 尝试转换和播放
            wav_file = tool.convert_opus_to_wav(opus_file)
            if wav_file:
                tool.play_audio_file(wav_file, 'wav')

                # 清理临时文件
                try:
                    os.remove(wav_file)
                except:
                    pass


if __name__ == "__main__":
    main()