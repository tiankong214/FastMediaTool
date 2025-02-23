import PyInstaller.__main__
import os
import sys

def build():
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(current_dir, 'src')
    
    # 添加src目录到Python路径
    if src_dir not in sys.path:
        sys.path.append(src_dir)
    
    # 图标路径
    icon_path = os.path.join(current_dir, 'src', 'resources', 'icons', 'app.ico')
    
    # PyInstaller参数
    args = [
        os.path.join(current_dir, 'src', 'main.py'),  # 主程序文件
        '--name=音视频处理工作台',  # 输出文件名
        '--windowed',  # 使用窗口模式，不显示控制台
        '--noconsole',  # 不显示控制台窗口
        f'--icon={icon_path}',  # 应用图标
        '--noconfirm',  # 覆盖输出目录
        '--clean',  # 清理临时文件
        '--add-data', f'{os.path.join(current_dir, "src/resources")}:resources',  # 添加资源文件
        '--hidden-import=PIL',  # 添加隐式依赖
        '--hidden-import=cv2',
        '--hidden-import=moviepy',  # moviepy
        '--hidden-import=moviepy.editor',  # moviepy.editor
        '--hidden-import=proglog',  # moviepy 依赖
        '--hidden-import=tqdm',  # moviepy 依赖
        '--hidden-import=decorator',  # moviepy 依赖
        '--hidden-import=imageio',  # moviepy 依赖
        '--hidden-import=imageio_ffmpeg',  # moviepy 依赖
        '--hidden-import=ui',
        '--hidden-import=video_tools',
        '--onedir',
        '--paths', src_dir,
        '--collect-all', 'moviepy',
        '--add-data', f'{os.path.join(current_dir, "resources", "ffmpeg.exe")};resources',
        '--add-data', f'{os.path.join(current_dir, "resources", "ffprobe.exe")};resources',
    ]
    
    # 执行打包
    PyInstaller.__main__.run(args)

if __name__ == '__main__':
    build() 