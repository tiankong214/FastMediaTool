import os
import sys
import shutil
import tempfile
import stat
from typing import Optional

class ResourceManager:
    _instance = None
    _temp_dir: Optional[str] = None
    _ffmpeg_path: Optional[str] = None
    _ffprobe_path: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResourceManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self._extract_resources()

    def _make_executable(self, path: str):
        """确保文件是可执行的"""
        # 添加执行权限
        current_mode = os.stat(path).st_mode
        os.chmod(path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _extract_resources(self):
        """提取打包的资源文件"""
        try:
            # 获取基础路径
            if getattr(sys, 'frozen', False):
                # 如果是打包后的程序
                base_path = sys._MEIPASS
                print(f"运行于打包环境，基础路径: {base_path}")
            else:
                # 如果是开发环境
                base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'resources'))
                print(f"运行于开发环境，基础路径: {base_path}")

            # 创建临时目录
            self._temp_dir = tempfile.mkdtemp(prefix='fastmediatool_')
            print(f"创建临时目录: {self._temp_dir}")

            # 复制 FFmpeg 文件到临时目录
            ffmpeg_src = os.path.join(base_path, 'ffmpeg.exe')
            ffprobe_src = os.path.join(base_path, 'ffprobe.exe')

            print(f"源文件路径:")
            print(f"FFmpeg: {ffmpeg_src}")
            print(f"FFprobe: {ffprobe_src}")

            if os.path.exists(ffmpeg_src) and os.path.exists(ffprobe_src):
                self._ffmpeg_path = os.path.join(self._temp_dir, 'ffmpeg.exe')
                self._ffprobe_path = os.path.join(self._temp_dir, 'ffprobe.exe')
                
                # 复制文件
                shutil.copy2(ffmpeg_src, self._ffmpeg_path)
                shutil.copy2(ffprobe_src, self._ffprobe_path)
                
                # 确保文件可执行
                self._make_executable(self._ffmpeg_path)
                self._make_executable(self._ffprobe_path)
                
                print(f"文件已提取并设置权限:")
                print(f"FFmpeg: {self._ffmpeg_path}")
                print(f"FFprobe: {self._ffprobe_path}")
            else:
                raise FileNotFoundError(
                    f"找不到 FFmpeg 文件:\n"
                    f"FFmpeg: {ffmpeg_src}\n"
                    f"FFprobe: {ffprobe_src}"
                )

        except Exception as e:
            print(f"提取资源文件失败: {str(e)}")
            if self._temp_dir and os.path.exists(self._temp_dir):
                try:
                    shutil.rmtree(self._temp_dir)
                except:
                    pass
            raise

    def cleanup(self):
        """清理临时文件"""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                # 确保进程不再使用这些文件
                if self._ffmpeg_path and os.path.exists(self._ffmpeg_path):
                    os.chmod(self._ffmpeg_path, stat.S_IWRITE)
                if self._ffprobe_path and os.path.exists(self._ffprobe_path):
                    os.chmod(self._ffprobe_path, stat.S_IWRITE)
                
                shutil.rmtree(self._temp_dir)
                self._temp_dir = None
                self._ffmpeg_path = None
                self._ffprobe_path = None
                print("临时文件已清理")
            except Exception as e:
                print(f"清理临时文件失败: {str(e)}")

    @property
    def ffmpeg_path(self) -> str:
        """获取 FFmpeg 路径"""
        if not self._ffmpeg_path or not os.path.exists(self._ffmpeg_path):
            raise FileNotFoundError("FFmpeg 路径未初始化或文件不存在")
        return self._ffmpeg_path

    @property
    def ffprobe_path(self) -> str:
        """获取 FFprobe 路径"""
        if not self._ffprobe_path or not os.path.exists(self._ffprobe_path):
            raise FileNotFoundError("FFprobe 路径未初始化或文件不存在")
        return self._ffprobe_path

    def __del__(self):
        self.cleanup() 