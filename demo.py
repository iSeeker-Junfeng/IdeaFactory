import opuslib
import numpy as np
import sounddevice as sd

# 参数设定
SAMPLE_RATE = 48000        # Opus 推荐采样率
CHANNELS = 1               # 通常是 1 或 2
FRAME_SIZE = 960           # 每帧采样数，20ms对应960个采样点（48000Hz）

# 初始化解码器
decoder = opuslib.Decoder(SAMPLE_RATE, CHANNELS)

# 打开裸流文件
with open("output.opus", "rb") as f:
    # 初始化播放
    sd.default.samplerate = SAMPLE_RATE
    sd.default.channels = CHANNELS

    def callback(outdata, frames, time, status):
        # 从文件中读取一个数据包
        packet = f.read(1275)  # Opus 最大帧长度为 1275 字节
        if not packet:
            raise sd.CallbackStop()

        # 解码为 PCM 数据
        pcm = decoder.decode(packet, FRAME_SIZE)
        # 转成 numpy 数组并播放
        outdata[:] = np.frombuffer(pcm, dtype=np.int16).reshape(-1, CHANNELS)

    # 开始流式播放
    with sd.OutputStream(callback=callback):
        sd.sleep(100000)  # 可自适应时长
