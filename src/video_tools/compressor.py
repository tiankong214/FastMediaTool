import cv2
import ffmpeg
import os
import subprocess
from typing import Tuple, Dict, Callable, Any
import re

class VideoCompressor:
    @staticmethod
    def get_video_info(file_path: str) -> Dict:
        """获取视频文件信息"""
        probe = ffmpeg.probe(file_path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        
        # 获取文件大小（MB）
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        
        return {
            'width': int(video_info['width']),
            'height': int(video_info['height']),
            'duration': float(probe['format']['duration']),
            'size': round(file_size, 2),
            'format': probe['format']['format_name']
        }
    
    @staticmethod
    def compress_video(input_path: str, output_path: str, resolution: str,
                      progress_callback: Callable[[int], bool], worker: Any = None) -> bool:
        """压缩视频"""
        try:
            # 获取输出分辨率
            output_resolution = VideoCompressor.parse_resolution(resolution)
            if not output_resolution:
                print("无法解析分辨率设置")
                return False

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # 构建 FFmpeg 命令
            command = [
                'ffmpeg', '-y',  # 覆盖已存在的文件
                '-i', input_path,
                '-c:v', 'libx264',  # 使用 H.264 编码
                '-preset', 'veryfast',  # 使用最快的编码速度预设
                '-tune', 'fastdecode',  # 优化解码速度
                '-crf', '23',  # 画质控制
                '-c:a', 'aac',  # 音频编码
                '-b:a', '128k',  # 音频比特率
                '-movflags', '+faststart',  # 优化网络播放
                '-threads', '0'  # 使用所有可用CPU线程
            ]

            # 如果不是保持原始分辨率，添加分辨率参数
            if resolution != "原始分辨率":
                width, height = output_resolution
                command.extend(['-vf', f'scale={width}:{height}'])

            # 添加输出文件路径
            command.append(output_path)

            print(f"执行命令: {' '.join(command)}")

            # 创建进程，使用 utf-8 编码
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8',
                errors='replace',  # 处理无法解码的字符
                universal_newlines=True
            )

            if worker:
                worker.process = process

            # 读取输出并更新进度
            duration = VideoCompressor.get_video_info(input_path)['duration']
            current_time = 0

            while True:
                try:
                    line = process.stderr.readline()
                    if not line and process.poll() is not None:
                        break

                    if line:
                        print(f"FFmpeg: {line.strip()}")
                        # 从输出中提取时间信息
                        time_match = re.search(r'time=(\d+:\d+:\d+.\d+)', line)
                        if time_match:
                            time_str = time_match.group(1)
                            current_time = VideoCompressor.parse_time(time_str)
                            if duration > 0:
                                progress = min(int((current_time / duration) * 100), 100)
                                if not progress_callback(progress):
                                    process.terminate()
                                    process.wait()
                                    print("压缩已取消")
                                    return False
                except UnicodeDecodeError as e:
                    print(f"解码错误（忽略）: {str(e)}")
                    continue

            # 检查进程返回码
            return_code = process.poll()
            print(f"FFmpeg 进程返回码: {return_code}")

            if return_code != 0:
                try:
                    stderr_output = process.stderr.read()
                    print(f"FFmpeg 错误输出: {stderr_output}")
                except UnicodeDecodeError:
                    print("无法读取错误输出（编码问题）")
                return False

            # 验证输出文件
            if not os.path.exists(output_path):
                print("输出文件不存在")
                return False

            output_size = os.path.getsize(output_path)
            if output_size == 0:
                print("输出文件大小为0")
                return False

            print("压缩完成")
            return True

        except Exception as e:
            print(f"压缩过程出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def parse_time(time_str: str) -> float:
        """解析 FFmpeg 时间字符串为秒数"""
        try:
            h, m, s = time_str.split(':')
            return float(h) * 3600 + float(m) * 60 + float(s)
        except:
            return 0.0

    @staticmethod
    def parse_resolution(resolution: str) -> Tuple[int, int] | None:
        """解析分辨率字符串为宽度和高度"""
        if resolution == "原始分辨率":
            return None
        elif "4K" in resolution:
            return (3840, 2160)
        elif "2K" in resolution:
            return (2560, 1440)
        elif "1080P" in resolution:
            return (1920, 1080)
        elif "720P" in resolution:
            return (1280, 720)
        elif "480P" in resolution:
            return (854, 480)
        elif "360P" in resolution:
            return (640, 360)
        else:
            print(f"无法解析的分辨率: {resolution}")
            return None 