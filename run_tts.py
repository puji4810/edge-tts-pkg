import asyncio
import argparse
import tempfile
import os
import sys
import math
from edge_tts import Communicate
from pydub import AudioSegment

# 定义一个异步主函数
async def main():
    # 1. 设置命令行参数解析
    parser = argparse.ArgumentParser(description="增强版TTS工具，支持格式转换、音量和采样率调整。")
    
    # 支持两种文本输入方式：直接传递或从文件读取
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument("--text", type=str, help="要转换为语音的文本")
    text_group.add_argument("--text-file", type=str, help="包含要转换文本的文件路径")
    
    parser.add_argument("--voice", type=str, default="en-US-SteffanNeural", help="要使用的语音。")
    parser.add_argument("--output", type=str, required=True, help="最终输出的音频文件路径。")
    # --- 格式控制参数 ---
    parser.add_argument("--format", type=str, default="wav", choices=['wav', 'mp3'], help="输出音频格式 (wav 或 mp3)。")
    parser.add_argument("--sample_rate", type=int, default=44100, help="输出WAV文件的采样率 (例如: 44100, 22050)。")
    parser.add_argument("--volume", type=int, default=50, help="音量大小，0-100的百分比。")
    # --- 语音风格参数 ---
    parser.add_argument("--speech_rate", type=int, default=0, help="语速调整，百分比 (例如: -10, 20)。")
    parser.add_argument("--pitch_rate", type=int, default=0, help="音调调整，百分比 (例如: -10, 20)。")
    
    args = parser.parse_args()

    # 2. 获取要转换的文本
    text = ""
    if args.text:
        text = args.text
    elif args.text_file:
        # 确保文件路径是绝对路径
        text_file = os.path.abspath(args.text_file)
        try:
            # 检查文件是否存在
            if not os.path.exists(text_file):
                print(f"错误：文件不存在: {text_file}")
                sys.exit(1)
                
            with open(text_file, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            # 注意：不在这里删除临时文件，让调用方（Go代码）负责清理
        except Exception as e:
            print(f"错误：无法读取文件 {text_file}: {e}")
            sys.exit(1)
    
    if not text:
        print("错误：没有提供有效的文本内容")
        sys.exit(1)
    
    # 确保输出路径是绝对路径
    output_file = os.path.abspath(args.output)
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)

    # 将百分比速率/音调转换为edge-tts需要的格式
    rate_str = f"{args.speech_rate:+d}%"
    pitch_str = f"{args.pitch_rate:+d}Hz" # Pitch in edge-tts is often better controlled with Hz

    # 创建一个临时的MP3文件来保存原始音频流
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmpfile:
        tmp_filename = tmpfile.name
    
    try:
        # 3. 调用 edge-tts 生成原始音频
        print(f"步骤1: 正在从Edge TTS获取原始音频流 (MP3)...")
        communicate = Communicate(text, args.voice, rate=rate_str, pitch=pitch_str)
        await communicate.save(tmp_filename)
        print(f"原始音频已保存到临时文件: {tmp_filename}")

        # 4. 使用 pydub 进行音频后处理
        print(f"步骤2: 正在使用pydub进行后处理...")
        
        # 从临时MP3文件加载音频
        audio = AudioSegment.from_mp3(tmp_filename)

        # 调整音量
        # pydub使用分贝(dB)为单位。我们将0-100的音量映射到一个合理的分贝范围。
        # 这里一个简单的映射：50 -> -6dB (响度约减半), 100 -> 0dB (原音量)
        # 您可以根据需要调整这个映射逻辑
        if args.volume == 100:
            db_change = 0
        else:
            # 将 0-100 映射到 -30dB 到 0dB 的范围
            db_change = -30 * (1 - args.volume / 100)
        
        print(f"音量调整: {args.volume}% -> {db_change:.2f} dB")
        audio = audio + db_change

        # 如果输出格式是WAV，则进行重采样
        if args.format == 'wav':
            print(f"设置采样率到: {args.sample_rate} Hz")
            audio = audio.set_frame_rate(args.sample_rate)
            # 设置为单声道
            audio = audio.set_channels(1)

        # 5. 导出最终文件
        print(f"步骤3: 正在导出最终文件到: {args.output}")
        audio.export(args.output, format=args.format)
        
        print(f"成功！最终文件已生成: {args.output}")

    except Exception as e:
        print(f"错误：处理过程中发生异常: {e}")
        sys.exit(1)
    finally:
        # 6. 清理临时文件
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)
            print(f"临时文件 {tmp_filename} 已删除。")


if __name__ == "__main__":
    asyncio.run(main())