import os
import sys
import subprocess
import shutil

def build():
    try:
        # 获取当前目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 检查FFmpeg文件
        ffmpeg_src = os.path.join(current_dir, 'resources', 'ffmpeg.exe')
        ffprobe_src = os.path.join(current_dir, 'resources', 'ffprobe.exe')
        if not os.path.exists(ffmpeg_src) or not os.path.exists(ffprobe_src):
            raise FileNotFoundError("请将ffmpeg.exe和ffprobe.exe放入resources目录")
        
        # 清理之前的构建
        for dir_name in ['build', 'dist']:
            if os.path.exists(dir_name):
                print(f"清理 {dir_name} 目录...")
                shutil.rmtree(dir_name)
        
        # 运行PyInstaller
        print("开始打包...")
        result = subprocess.run(
            ['pyinstaller', '音视频处理工作台.spec', '--noconfirm'],
            capture_output=True,
            text=True
        )
        
        # 检查结果
        if result.returncode == 0:
            dist_dir = os.path.join(current_dir, 'dist', '音视频处理工作台')
            if os.path.exists(dist_dir):
                print("打包成功！")
                print(f"输出目录: {dist_dir}")
            else:
                print("打包似乎成功了，但找不到输出目录")
        else:
            print("打包失败！")
            print("错误信息:")
            print(result.stderr)
            
    except Exception as e:
        print(f"打包过程出错: {str(e)}")
        raise

if __name__ == '__main__':
    build() 