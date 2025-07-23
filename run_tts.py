import asyncio
import argparse
import tempfile
import os
import sys
import math
import codecs
from edge_tts import Communicate
from pydub import AudioSegment

sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 定义一个异步主函数
async def main():
    # 1. 设置命令行参数解析
    parser = argparse.ArgumentParser(description="Enhanced TTS tool with format conversion, volume and sample rate adjustment.")
    
    # 支持两种文本输入方式：直接传递或从文件读取
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument("--text", type=str, help="Text to convert to speech")
    text_group.add_argument("--text-file", type=str, help="File path containing text to convert")
    
    parser.add_argument("--voice", type=str, default="en-US-SteffanNeural", help="Voice to use.")
    parser.add_argument("--output", type=str, required=True, help="Final output audio file path.")
    # --- 格式控制参数 ---
    parser.add_argument("--format", type=str, default="wav", choices=['wav', 'mp3'], help="Output audio format (wav or mp3).")
    parser.add_argument("--sample_rate", type=int, default=44100, help="Output WAV file sample rate (e.g.: 44100, 22050).")
    parser.add_argument("--volume", type=int, default=50, help="Volume level, percentage from 0-100.")
    # --- 语音风格参数 ---
    parser.add_argument("--speech_rate", type=int, default=0, help="Speech rate adjustment, percentage (e.g.: -10, 20).")
    parser.add_argument("--pitch_rate", type=int, default=0, help="Pitch adjustment, percentage (e.g.: -10, 20).")
    
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
                print(f"Error: File does not exist: {text_file}")
                sys.exit(1)
                
            with open(text_file, 'r', encoding='utf-8') as f:
                text = f.read().strip()
            # 注意：不在这里删除临时文件，让调用方（Go代码）负责清理
        except Exception as e:
            print(f"Error: Unable to read file {text_file}: {e}")
            sys.exit(1)
    
    if not text:
        print("Error: No valid text content provided")
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
        print(f"Step 1: Getting raw audio stream from Edge TTS (MP3)...")
        communicate = Communicate(text, args.voice, rate=rate_str, pitch=pitch_str)
        await communicate.save(tmp_filename)
        print(f"Raw audio saved to temp file: {tmp_filename}")

        # 4. 使用 pydub 进行音频后处理
        print(f"Step 2: Post-processing with pydub...")
        
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
        
        print(f"Volume adjustment: {args.volume}% -> {db_change:.2f} dB")
        audio = audio + db_change

        # 如果输出格式是WAV，则进行重采样
        if args.format == 'wav':
            print(f"Setting sample rate to: {args.sample_rate} Hz")
            audio = audio.set_frame_rate(args.sample_rate)
            # 设置为单声道
            audio = audio.set_channels(1)

        # 5. 导出最终文件
        print(f"Step 3: Exporting final file to: {args.output}")
        audio.export(args.output, format=args.format)
        
        print(f"Success! Final file generated: {args.output}")

    except Exception as e:
        print(f"Error: Exception occurred during processing: {e}")
        sys.exit(1)
    finally:
        # 6. 清理临时文件
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)
            print(f"Temp file {tmp_filename} deleted.")


if __name__ == "__main__":
    asyncio.run(main())