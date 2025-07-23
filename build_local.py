#!/usr/bin/env python3
"""
本地构建脚本，用于测试EdgeTTS CLI的打包
使用方法: python build_local.py
"""

import os
import sys
import subprocess
import platform

def run_command(cmd, cwd=None):
    """运行命令并打印输出"""
    print(f"执行命令: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def main():
    # 获取当前平台信息
    current_platform = platform.system().lower()
    print(f"当前平台: {current_platform}")
    
    # 确保在edge-tts-pkg目录中
    if not os.path.exists("run_tts.py"):
        print("错误: 请在edge-tts-pkg目录中运行此脚本")
        sys.exit(1)
    
    # 安装依赖
    print("1. 安装Python依赖...")
    if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]):
        print("安装依赖失败")
        sys.exit(1)
    
    if not run_command([sys.executable, "-m", "pip", "install", "pyinstaller"]):
        print("安装PyInstaller失败")
        sys.exit(1)
    
    # 构建可执行文件
    print("2. 使用PyInstaller构建可执行文件...")
    
    # 根据平台确定输出文件名
    if current_platform == "windows":
        output_name = "edge-tts-windows.exe"
    elif current_platform == "linux":
        output_name = "edge-tts-linux"
    elif current_platform == "darwin":
        output_name = "edge-tts-macos"
    else:
        output_name = f"edge-tts-{current_platform}"
    
    # PyInstaller命令
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        "--name", "edge-tts",
        "run_tts.py"
    ]
    
    if not run_command(pyinstaller_cmd):
        print("PyInstaller构建失败")
        sys.exit(1)
    
    # 重命名输出文件
    print("3. 重命名输出文件...")
    dist_dir = "dist"
    
    if current_platform == "windows":
        original_file = os.path.join(dist_dir, "edge-tts.exe")
    else:
        original_file = os.path.join(dist_dir, "edge-tts")
    
    final_file = os.path.join(dist_dir, output_name)
    
    if os.path.exists(original_file):
        os.rename(original_file, final_file)
        print(f"文件重命名为: {final_file}")
    else:
        print(f"错误: 找不到构建的文件 {original_file}")
        sys.exit(1)
    
    # 测试可执行文件
    print("4. 测试可执行文件...")
    
    # 创建测试输入文件
    test_input = "test_input.txt"
    test_output = "test_output.wav"
    
    with open(os.path.join(dist_dir, test_input), "w", encoding="utf-8") as f:
        f.write("Hello World, this is a test.")
    
    # 测试命令
    test_cmd = [
        os.path.join(".", output_name),
        "--text-file", test_input,
        "--output", test_output,
        "--voice", "en-US-SteffanNeural",
        "--volume", "50"
    ]
    
    if run_command(test_cmd, cwd=dist_dir):
        test_output_path = os.path.join(dist_dir, test_output)
        if os.path.exists(test_output_path):
            print(f"✅ 测试成功! 生成的音频文件: {test_output_path}")
            print(f"✅ 可执行文件构建完成: {final_file}")
        else:
            print("❌ 测试失败: 没有生成音频文件")
    else:
        print("❌ 测试失败: 可执行文件运行出错")
    
    print("\n构建完成!")
    print(f"可执行文件位置: {os.path.abspath(final_file)}")

if __name__ == "__main__":
    main() 