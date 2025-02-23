import av
from av.video.frame import VideoFrame
from av.video.plane import VideoPlane
from av.audio.frame import AudioFrame
from av.container import Container
from av.stream import Stream
from av.codec.context import CodecContext
from av.video.codeccontext import VideoCodecContext
from av.audio.codeccontext import AudioCodecContext
from fractions import Fraction
from typing import Dict, Any, Optional, Union, Tuple, Callable, List, TextIO, cast
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import queue
import threading
import shutil
import logging
import os
import time
import traceback
import importlib.util

class VideoCompressor:
    last_progress_time = 0  # 上次进度更新时间
    last_progress_value = -1  # 上次进度值
    last_log_message = ""  # 上次日志消息
    encode_lock = threading.Lock()  # 添加编码锁
    
    @staticmethod
    def log_message(worker: Any, message: str, level: str = "INFO") -> None:
        """记录日志，避免重复"""
        if message != VideoCompressor.last_log_message:
            worker.log(message, level)
            VideoCompressor.last_log_message = message
    
    @staticmethod
    def log_progress(worker: Any, progress: int) -> None:
        """记录进度，避免重复且控制频率"""
        current_time = time.time()
        progress_message = f"压缩进度：{progress}%"
        
        # 只有当进度值变化且距离上次更新超过1秒时才记录
        if (progress != VideoCompressor.last_progress_value and 
            current_time - VideoCompressor.last_progress_time >= 1.0 and
            progress_message != VideoCompressor.last_log_message):  # 添加消息内容检查
            
            worker.log(progress_message, "INFO")
            VideoCompressor.last_progress_time = current_time
            VideoCompressor.last_progress_value = progress
            VideoCompressor.last_log_message = progress_message  # 更新最后的消息

    @staticmethod
    def get_video_info(file_path: str) -> Dict[str, Union[int, float, str]]:
        """获取视频信息"""
        result: Dict[str, Union[int, float, str]] = {
            'width': 0,
            'height': 0,
            'duration': 0,
            'frames': 0,
            'fps': 0.0,
            'size': 0.0,
            'format': 'unknown'
        }
        
        try:
            with av.open(file_path) as container:
                if not container.streams.video:
                    return result
                    
                stream = container.streams.video[0]
                
                # 安全地获取帧率
                fps = float(stream.average_rate or 0)
                
                # 使用类型安全的方式更新字典
                updates: Dict[str, Union[int, float, str]] = {
                    'width': int(stream.width or 0),
                    'height': int(stream.height or 0),
                    'format': str(stream.format.name if stream.format else 'unknown'),
                    'duration': float(container.duration / av.time_base) if container.duration else 0.0,
                    'frames': int(stream.frames or 0),
                    'fps': fps,
                    'size': os.path.getsize(file_path) / (1024 * 1024)
                }
                result.update(updates)
                
                # 添加格式验证
                if result['format'] not in ['yuv420p', 'nv12', 'rgb24']:
                    logging.warning(f"非常用视频格式: {result['format']}")
                    
                return result
                
        except Exception as e:
            logging.error(f"获取视频信息失败: {str(e)}")
            return result
        
        # 添加一个最终的返回语句，确保所有路径都有返回值
        return result

    @staticmethod
    def copy_frame(
        frame: VideoFrame,
        width: Optional[int] = None,
        height: Optional[int] = None,
        format_name: Optional[str] = None
    ) -> VideoFrame:
        """创建帧的完整副本"""
        try:
            # 在方法开始添加调试信息
            logging.debug(f"处理帧: width={frame.width}, height={frame.height}, "
                        f"format={frame.format}, planes={len(frame.planes)}")
            # 验证输入帧
            if not frame or not frame.format:
                raise RuntimeError("输入帧格式无效")

            # 获取源帧格式名称
            source_format = frame.format.name if frame.format else 'yuv420p'
            target_format = format_name or source_format

            # 记录格式信息
            logging.debug(f"源帧格式: {source_format}, 目标格式: {target_format}")

            # 如果需要调整大小或格式
            if width or height or (format_name and format_name != source_format):
                new_frame = frame.reformat(
                    width=width or frame.width,
                    height=height or frame.height,
                    format=target_format
                )
                if not new_frame:
                    raise RuntimeError("帧重新格式化失败")
                return new_frame

            # 如果不需要调整，直接返回原始帧
            return frame

        except Exception as e:
            error_msg = f"帧处理失败: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    @staticmethod
    def encode_chunk(frames: List[VideoFrame], video_stream, output_queue: Queue):
        """编码一组帧"""
        try:
            packets = []
            for i, frame in enumerate(frames):
                try:
                    if not frame:
                        raise RuntimeError("输入帧无效")

                    # 直接使用原始帧进行编码
                    with VideoCompressor.encode_lock:
                        new_packets = video_stream.encode(frame)
                        if new_packets:
                            packets.extend(new_packets)

                except Exception as e:
                    error_msg = f"处理帧 {i} 时出错: {str(e)}\n{traceback.format_exc()}"
                    logging.error(error_msg)
                    output_queue.put(('error', error_msg))
                    return

            if packets:
                output_queue.put(('video', packets))

        except Exception as e:
            error_msg = f"编码过程错误: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            output_queue.put(('error', error_msg))

    @staticmethod
    def calculate_progress(frame_count: int, total_frames: int, frame_pts: Optional[int], duration: Optional[int]) -> int:
        """计算进度百分比"""
        try:
            # 优先使用帧数计算进度
            if total_frames > 0:
                return int((frame_count * 100) / total_frames)
            
            # 如果没有总帧数，使用时间戳计算
            if frame_pts is not None and duration is not None and duration > 0:
                return int((frame_pts * 100) / duration)
            
            # 如果都无法计算，返回0
            return 0
        except:
            return 0

    @staticmethod
    def compress_video(
        input_file: str,
        output_file: str,
        resolution: str,
        progress_callback: Optional[Callable[[int], bool]] = None,
        worker: Any = None
    ) -> bool:
        """压缩视频"""
        try:
            # 构建 FFmpeg 命令
            command = [
                'ffmpeg', '-y',
                '-i', input_file,
                '-c:v', 'h264_nvenc' if VideoCompressor.has_nvidia_gpu() else 'libx264',
                '-pix_fmt', 'yuv420p',  # 强制指定像素格式
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k'
            ]

            # 添加分辨率参数
            output_resolution = VideoCompressor.parse_resolution(resolution)
            if output_resolution:
                command.extend([
                    '-vf', f'scale={output_resolution[0]}:{output_resolution[1]}:flags=lanczos'
                ])

            command.append(output_file)

            # 记录命令
            logging.info(f"执行命令: {' '.join(command)}")
            if worker:
                VideoCompressor.log_message(worker, f"开始压缩: {input_file}", "INFO")

            # 执行命令并监控进度
            process = subprocess.Popen(
                command,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )

            # 确保 stderr 存在且是文本流
            if process.stderr is None:
                raise RuntimeError("无法获取进程输出")

            stderr = cast(TextIO, process.stderr)
            duration = None

            # 读取输出
            while True:
                try:
                    line = stderr.readline()
                    if not line:
                        break

                    # 解析时长信息
                    if not duration and "Duration:" in line:
                        duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})", line)
                        if duration_match:
                            h, m, s = map(int, duration_match.groups())
                            duration = h * 3600 + m * 60 + s
                            if worker:
                                VideoCompressor.log_message(
                                    worker, 
                                    f"视频时长: {h:02d}:{m:02d}:{s:02d}",
                                    "INFO"
                                )

                    # 解析进度信息
                    time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})", line)
                    if time_match and duration:
                        h, m, s = map(int, time_match.groups())
                        time_processed = h * 3600 + m * 60 + s
                        progress = int((time_processed * 100) / duration)
                        
                        if worker:
                            VideoCompressor.log_progress(worker, progress)
                        if progress_callback and not progress_callback(progress):
                            process.terminate()
                            return False

                except Exception as e:
                    logging.error(f"读取进程输出失败: {str(e)}")
                    break

            result = process.wait() == 0
            if result:
                if worker:
                    VideoCompressor.log_message(worker, "压缩完成", "INFO")
                return True
            else:
                raise RuntimeError("FFmpeg 处理失败")

        except Exception as e:
            error_msg = f"压缩失败: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            if worker:
                VideoCompressor.log_message(worker, f"压缩失败: {str(e)}", "ERROR")
            return False

    @staticmethod
    def parse_resolution(resolution: str) -> Optional[Tuple[int, int]]:
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
            logging.warning(f"无法解析的分辨率: {resolution}")
            return None

    @staticmethod
    def has_nvidia_gpu() -> bool:
        """检查是否有NVIDIA GPU可用"""
        try:
            # 尝试导入 pynvml
            pynvml_spec = importlib.util.find_spec("pynvml")
            if pynvml_spec is None:
                logging.info("未找到 pynvml 模块，将使用 CPU 编码")
                return False

            # 动态导入 pynvml
            pynvml = importlib.util.module_from_spec(pynvml_spec)
            if pynvml_spec.loader:
                pynvml_spec.loader.exec_module(pynvml)
            else:
                logging.info("无法加载 pynvml 模块，将使用 CPU 编码")
                return False

            # 初始化 NVML
            try:
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                pynvml.nvmlShutdown()
                
                if device_count > 0:
                    logging.info(f"找到 {device_count} 个 NVIDIA GPU，将使用 GPU 编码")
                    return True
                else:
                    logging.info("未找到 NVIDIA GPU，将使用 CPU 编码")
                    return False
                    
            except Exception as e:
                logging.info(f"NVML 初始化失败: {e}，将使用 CPU 编码")
                return False

        except ImportError as e:
            logging.info(f"导入 pynvml 失败: {e}，将使用 CPU 编码")
            return False
        except Exception as e:
            logging.info(f"检查 GPU 时出错: {e}，将使用 CPU 编码")
            return False

    @staticmethod
    def compress_video_gpu(
        input_file: str,
        output_file: str,
        output_resolution: Optional[Tuple[int, int]] = None,
        progress_callback: Optional[Callable[[int], bool]] = None,
        worker: Any = None
    ) -> bool:
        """使用 GPU 压缩视频"""
        try:
            # 使用 FFmpeg 命令行方式压缩
            command = [
                'ffmpeg', '-y',
                '-i', input_file,
                '-c:v', 'h264_nvenc',
                '-preset', 'p4',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k'
            ]

            # 添加分辨率参数
            if output_resolution:
                command.extend([
                    '-vf', f'scale={output_resolution[0]}:{output_resolution[1]}'
                ])

            command.append(output_file)

            # 执行命令
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # 等待完成
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                if worker:
                    VideoCompressor.log_message(worker, "压缩完成", "INFO")
                return True
            else:
                raise RuntimeError(f"FFmpeg 执行失败: {stderr}")

        except Exception as e:
            error_msg = f"GPU 压缩失败: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            if worker:
                VideoCompressor.log_message(worker, error_msg, "ERROR")
            return False

    @staticmethod
    def compress_video_cpu(
        input_file: str,
        output_file: str,
        output_resolution: Optional[Tuple[int, int]] = None,
        progress_callback: Optional[Callable[[int], bool]] = None,
        worker: Any = None
    ) -> bool:
        """使用 CPU 压缩视频"""
        try:
            # 使用 FFmpeg 命令行方式压缩
            command = [
                'ffmpeg', '-y',
                '-i', input_file,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k'
            ]

            # 添加分辨率参数
            if output_resolution:
                command.extend([
                    '-vf', f'scale={output_resolution[0]}:{output_resolution[1]}'
                ])

            command.append(output_file)

            # 执行命令
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # 等待完成
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                if worker:
                    VideoCompressor.log_message(worker, "压缩完成", "INFO")
                return True
            else:
                raise RuntimeError(f"FFmpeg 执行失败: {stderr}")

        except Exception as e:
            error_msg = f"CPU 压缩失败: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            if worker:
                VideoCompressor.log_message(worker, error_msg, "ERROR")
            return False

    @staticmethod
    def compress_video_ffmpeg(input_path: str, output_path: str, resolution: str,
                            progress_callback: Optional[Callable[[int], bool]] = None,
                            worker: Any = None) -> bool:
        """使用FFmpeg压缩视频"""
        try:
            output_resolution = VideoCompressor.parse_resolution(resolution)
            
            # 记录日志
            if hasattr(worker, 'log_widget'):
                worker.log_widget.log(f"目标分辨率：{output_resolution}")
            
            # 构建FFmpeg命令
            command = [
                'ffmpeg', '-y',  # 覆盖输出文件
                '-hide_banner',  # 隐藏版本信息
                '-loglevel', 'error',  # 只显示错误信息
                '-i', input_path,  # 输入文件
                '-c:v', 'h264_nvenc' if VideoCompressor.has_nvidia_gpu() else 'libx264',  # 视频编码器
                '-preset', 'p4' if VideoCompressor.has_nvidia_gpu() else 'fast',  # 编码速度
                '-crf', '23',  # 质量控制（调整为更合理的值）
                '-b:v', '0',  # 使用CRF模式时不限制码率
                '-c:a', 'aac',  # 音频编码器
                '-b:a', '192k',  # 音频码率
                '-movflags', '+faststart',  # 优化MP4结构
            ]
            
            # 添加分辨率参数
            if output_resolution:
                command.extend([
                    '-vf', f'scale={output_resolution[0]}:{output_resolution[1]}'
                ])
            
            command.append(output_path)  # 输出文件
            
            if hasattr(worker, 'log_widget'):
                worker.log_widget.log(f"开始压缩：{input_path}")
                worker.log_widget.log(f"FFmpeg命令：{' '.join(command)}")
            
            # 创建进程
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # 读取进程输出
            if process and process.stderr:
                stderr = cast(TextIO, process.stderr)
                if hasattr(stderr, 'readline'):  # 检查是否有 readline 方法
                    while True:
                        try:
                            line = stderr.readline()  # 使用本地引用
                            if not line:
                                break
                            # 处理输出...
                        except Exception as e:
                            if worker:
                                VideoCompressor.log_message(
                                    worker,
                                    f"读取输出失败: {str(e)}",
                                    "ERROR"
                                )
                            break

            # 收集错误输出
            error_output = []
            
            # 监控进度
            duration_value = 0  # 使用明确的整数类型
            time_processed = 0
            progress = 0  # 初始化进度值
            
            # 确保 stderr 是有效的文本流
            if process and process.stderr and isinstance(process.stderr, TextIO):
                stderr = cast(TextIO, process.stderr)
                while True:
                    try:
                        line = stderr.readline()
                        if not line:
                            break
                        
                        # 保存错误信息
                        error_output.append(line.strip())
                        
                        # 解析时长信息
                        if duration_value == 0 and "Duration:" in line:
                            duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})", line)
                            if duration_match:
                                h, m, s = map(int, duration_match.groups())
                                duration_value = h * 3600 + m * 60 + s
                                if hasattr(worker, 'log_widget'):
                                    worker.log_widget.log(f"视频时长：{h:02d}:{m:02d}:{s:02d}")
                        
                        # 解析进度信息
                        time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})", line)
                        if time_match and duration_value > 0:  # 确保有有效的持续时间
                            h, m, s = map(int, time_match.groups())
                            time_processed = h * 3600 + m * 60 + s
                            if duration_value > 0:  # 再次检查以确保不会除以0
                                progress = int((time_processed * 100) / duration_value)
                                if hasattr(worker, 'log_widget'):
                                    worker.log_widget.log(f"压缩进度：{progress}%", "DEBUG")
                                if progress_callback is not None and not progress_callback(progress):
                                    process.terminate()
                                    return False
                                
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        if worker:
                            VideoCompressor.log_message(worker, f"处理输出失败: {str(e)}", "ERROR")
                        break
            
            # 等待完成
            process.wait()
            
            if process.returncode == 0:
                if hasattr(worker, 'log_widget'):
                    worker.log_widget.log("压缩完成", "INFO")
                return True
            else:
                error_msg = "\n".join(error_output)
                raise RuntimeError(f"FFmpeg处理失败: {error_msg}")
                
        except Exception as e:
            if hasattr(worker, 'log_widget'):
                worker.log_widget.log(f"压缩失败: {str(e)}", "ERROR")
            return False

    @staticmethod
    def compress_video_stream(input_path: str, output_path: str, resolution: str,
                            progress_callback: Callable[[int], bool], worker: Any = None) -> bool:
        """使用流式处理压缩视频"""
        try:
            with av.open(input_path) as input_container:
                output_options = {
                    'c:v': 'h264_nvenc' if VideoCompressor.has_nvidia_gpu() else 'libx264',
                    'preset': 'p4' if VideoCompressor.has_nvidia_gpu() else 'fast',
                    'crf': '18',
                    'b:v': '5M',
                    'maxrate': '20M',
                    'bufsize': '20M',
                    'movflags': '+faststart',
                }
                
                with av.open(output_path, 'w', options=output_options) as output_container:
                    # 复制流配置
                    in_video = input_container.streams.video[0]
                    out_video = output_container.add_stream('h264', rate=in_video.rate)
                    
                    # 设置分辨率
                    output_resolution = VideoCompressor.parse_resolution(resolution)
                    if output_resolution:
                        out_video.width = output_resolution[0]
                        out_video.height = output_resolution[1]
                    else:
                        out_video.width = in_video.width
                        out_video.height = in_video.height
                    
                    # 复制音频流
                    if input_container.streams.audio:
                        out_audio = output_container.add_stream('aac')
                        out_audio.bit_rate = 192000
                    
                    # 处理视频
                    frame_count = 0
                    total_frames = int(in_video.frames or 0)  # 确保是整数
                    duration = int(in_video.duration or 1)  # 确保是整数且不为 None

                    for frame in input_container.decode(video=0):
                        if output_resolution:
                            frame = frame.reformat(
                                width=output_resolution[0],
                                height=output_resolution[1]
                            )
                        packets = out_video.encode(frame)
                        for packet in packets:
                            output_container.mux(packet)
                            
                        # 更新进度
                        frame_count += 1
                        progress = 0  # 默认进度值

                        try:
                            if total_frames > 0:
                                progress = int((frame_count * 100) / total_frames)
                            else:
                                pts = frame.pts
                                if pts is not None:
                                    pts_value = int(pts)
                                    progress = int((pts_value * 100) / duration) if duration > 0 else 0
                        except Exception:
                            progress = 0

                        if worker:
                            VideoCompressor.log_progress(worker, progress)
                        if not progress_callback(progress):
                            return False
                    
                    # 处理音频
                    if input_container.streams.audio:
                        for frame in input_container.decode(audio=0):
                            packets = out_audio.encode(frame)
                            for packet in packets:
                                output_container.mux(packet)
                    
                    # 刷新编码器
                    for packet in out_video.encode(None):
                        output_container.mux(packet)
                    if input_container.streams.audio:
                        for packet in out_audio.encode(None):
                            output_container.mux(packet)
            
            if worker:
                VideoCompressor.log_message(worker, "压缩完成", "INFO")
            return True
            
        except Exception as e:
            error_msg = f"压缩失败: {str(e)}\n"
            error_msg += f"错误类型: {type(e).__name__}\n"
            error_msg += f"堆栈跟踪:\n{traceback.format_exc()}"
            logging.error(error_msg)
            if worker:
                VideoCompressor.log_message(worker, error_msg, "ERROR")
            return False 