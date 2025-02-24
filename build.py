import os
import sys
import subprocess
import shutil
import time
import psutil
import signal

def kill_running_app():
    """结束正在运行的应用程序进程"""
    app_name = "音视频处理工作台.exe"
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == app_name:
                proc.kill()
                proc.wait()  # 等待进程结束
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def safe_remove_dir(dir_path, max_retries=5, delay=1):
    """安全地删除目录，带有重试机制"""
    for i in range(max_retries):
        try:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            return True
        except PermissionError:
            if i < max_retries - 1:
                # 尝试结束占用文件的进程
                kill_running_app()
                time.sleep(delay)
                continue
            return False
    return False

def handle_interrupt(signum, frame):
    """处理中断信号"""
    print("\n\n正在取消打包...")
    sys.exit(1)

def build():
    try:
        # 设置中断信号处理
        signal.signal(signal.SIGINT, handle_interrupt)
        
        print("开始打包程序...")
        print("1. 检查必要文件...")
        
        # 获取当前目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 检查FFmpeg和必要的DLL文件
        required_files = [
            'ffmpeg.exe',
            'ffprobe.exe',
            'avcodec-61.dll',
            'avdevice-61.dll',
            'avfilter-10.dll',
            'avformat-61.dll',
            'avutil-59.dll',
            'postproc-58.dll',
            'swresample-5.dll',
            'swscale-8.dll'
        ]
        
        # 检查所有必要文件
        missing_files = []
        for file_name in required_files:
            file_path = os.path.join(current_dir, 'resources', file_name)
            if not os.path.exists(file_path):
                missing_files.append(file_name)
        
        if missing_files:
            raise FileNotFoundError(
                f"以下文件缺失，请确保它们存在于resources目录中：\n"
                f"{', '.join(missing_files)}"
            )
        
        print("2. 清理旧的构建文件...")
        # 清理之前的构建
        for dir_name in ['build', 'dist']:
            if not safe_remove_dir(dir_name):
                raise PermissionError(f"无法删除 {dir_name} 目录，请确保程序未在运行")
        
        print("3. 准备打包环境...")
        # 确保 src 目录存在
        src_dir = os.path.join(current_dir, 'src')
        if not os.path.exists(src_dir):
            raise FileNotFoundError(f"找不到源代码目录: {src_dir}")
        
        print("4. 开始打包...")
        print("正在打包，请稍候...")
        
        # 修改构建命令
        command = [
            'pyinstaller',
            '--noconfirm',
            '--clean',
            '--name=音视频处理工作台',
            '--icon=resources/icon.ico',
            f'--paths={src_dir}',
            '--add-data=resources/ffmpeg.exe;.',
            '--add-data=resources/ffprobe.exe;.',
            '--add-data=resources/avcodec-61.dll;.',
            '--add-data=resources/avdevice-61.dll;.',
            '--add-data=resources/avfilter-10.dll;.',
            '--add-data=resources/avformat-61.dll;.',
            '--add-data=resources/avutil-59.dll;.',
            '--add-data=resources/postproc-58.dll;.',
            '--add-data=resources/swresample-5.dll;.',
            '--add-data=resources/swscale-8.dll;.',
            '--add-data=resources/icon.ico;resources',
            '--add-data=src/resources;resources',
            '--add-data=src/version.py;.',
            '--hidden-import=PIL',
            '--hidden-import=cv2',
            '--hidden-import=PyQt6.QtCore',
            '--hidden-import=PyQt6.QtGui',
            '--hidden-import=PyQt6.QtWidgets',
            '--hidden-import=PyQt6.sip',
            '--hidden-import=moviepy',
            '--hidden-import=moviepy.editor',
            '--hidden-import=proglog',
            '--hidden-import=tqdm',
            '--hidden-import=decorator',
            '--hidden-import=imageio',
            '--hidden-import=imageio_ffmpeg',
            '--hidden-import=ui',
            '--hidden-import=video_tools',
            '--hidden-import=version',
            '--hidden-import=typing',
            '--hidden-import=src.ui',
            '--hidden-import=src.ui.main_window',
            '--hidden-import=src.video_tools',
            '--hidden-import=src.utils',
            '--log-level=INFO',
            '--windowed',
            os.path.join(src_dir, 'main.py')
        ]

        # 直接使用 subprocess.run 而不是 Popen
        print("执行 PyInstaller 命令...")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # 检查结果
        if result.returncode == 0:
            print("\n打包成功！")
            dist_dir = os.path.join(current_dir, 'dist', '音视频处理工作台')
            if os.path.exists(dist_dir):
                print(f"输出目录: {dist_dir}")
            else:
                print("警告：找不到输出目录")
        else:
            print("\n打包失败！")
            print("错误信息:")
            print(result.stderr)
            
            # 保存详细错误日志
            with open('build_error.log', 'w', encoding='utf-8') as f:
                f.write("=== STDOUT ===\n")
                f.write(result.stdout)
                f.write("\n=== STDERR ===\n")
                f.write(result.stderr)
            print("\n详细错误信息已保存到 build_error.log")

    except Exception as e:
        print(f"\n打包过程出错: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        build()
    except KeyboardInterrupt:
        print("\n\n打包被用户取消")
    except Exception as e:
        print(f"\n打包过程出错: {str(e)}")
    finally:
        input("\n按回车键退出...") 