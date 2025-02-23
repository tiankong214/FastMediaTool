import subprocess
import os
import av
from typing import Callable, Any, List, Dict, Union, cast

class VideoSplitter:
    MAX_SIZE = 50  # MB，最大分段大小
    
    @staticmethod
    def split_video(input_path: str, progress_callback: Callable[[int], bool],
                   worker: Any = None, output_dir: str | None = None) -> bool:
        """分割视频"""
        try:
            # 获取视频信息
            info = VideoSplitter.get_video_info(input_path)
            total_duration = float(info['duration'])
            total_size = float(info['size'])
            
            if worker:
                worker.log(f"视频总时长: {total_duration}秒", "INFO")
                worker.log(f"视频总大小: {total_size:.2f}MB", "INFO")
            
            # 创建输出目录
            if not output_dir:
                output_dir = os.path.dirname(input_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取基础文件名
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            
            # 初始化变量
            current_time = 0
            part_index = 1
            
            while current_time < total_duration:
                if worker:
                    worker.log(f"开始处理第 {part_index} 段", "INFO")
                
                # 预估当前段时长（假设大小和时长成正比）
                estimated_duration = min(
                    int(VideoSplitter.MAX_SIZE / (total_size / total_duration)),
                    total_duration - current_time
                )
                
                # 尝试分割并检查大小
                output_path = os.path.join(output_dir, f"{base_name}_{part_index:03d}.mp4")
                
                # 修改 FFmpeg 命令执行部分
                command = [
                    'ffmpeg', '-y',
                    '-hide_banner',
                    '-loglevel', 'error',  # 改为 error 级别
                    '-i', input_path.encode('utf-8').decode('utf-8'),
                    '-ss', str(current_time),
                    '-t', str(estimated_duration),
                    '-c', 'copy',
                    '-avoid_negative_ts', '1',
                    output_path.encode('utf-8').decode('utf-8')
                ]
                
                # 添加 startupinfo 来隐藏命令窗口
                startupinfo = None
                if os.name == 'nt':  # Windows 系统
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    encoding='utf-8',
                    startupinfo=startupinfo  # 添加 startupinfo
                )
                
                process.wait()
                
                # 检查文件大小
                if os.path.exists(output_path):
                    size = os.path.getsize(output_path) / (1024 * 1024)  # MB
                    if size > VideoSplitter.MAX_SIZE:
                        # 如果超过50MB，减少时长重试
                        os.remove(output_path)
                        estimated_duration = int(estimated_duration * 0.9)  # 减少10%
                        continue
                
                # 更新进度
                progress = int((current_time / total_duration) * 100)
                if not progress_callback(progress):
                    return False
                
                current_time += estimated_duration
                part_index += 1
            
            progress_callback(100)
            return True
            
        except Exception as e:
            if worker:
                worker.log(f"分割失败: {str(e)}", "ERROR")
            return False

    @staticmethod
    def get_segment_info(input_path: str, segment_duration: int) -> List[dict]:
        """获取分段信息"""
        try:
            # 获取视频总时长
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                input_path
            ]
            duration = float(subprocess.check_output(probe_cmd).decode().strip())
            
            # 计算分段数
            segment_count = int((duration + segment_duration - 1) // segment_duration)
            
            # 生成分段信息
            segments = []
            for i in range(segment_count):
                start = i * segment_duration
                end = min((i + 1) * segment_duration, duration)
                segments.append({
                    'index': i + 1,
                    'start': start,
                    'end': end,
                    'duration': end - start
                })
            
            return segments
            
        except Exception as e:
            raise RuntimeError(f"获取分段信息失败: {str(e)}")

    @staticmethod
    def get_video_info(file_path: str) -> Dict[str, Union[int, float, str]]:
        """获取视频信息"""
        # 定义默认返回值
        default_info: Dict[str, Union[int, float, str]] = {
            'width': 0,
            'height': 0,
            'duration': 0.0,
            'size': 0.0,
            'format': '',
            'frame_rate': 0.0
        }
        
        try:
            with av.open(file_path) as container:
                # 获取视频流
                if not container.streams.video:
                    return default_info
                    
                stream = container.streams.video[0]
                
                # 获取时长（以秒为单位）
                duration = float(container.duration or 0) / av.time_base
                
                # 获取文件大小（MB）
                size = os.path.getsize(file_path) / (1024 * 1024)
                
                return {
                    'width': int(stream.width or 0),
                    'height': int(stream.height or 0),
                    'duration': float(duration),
                    'size': float(size),
                    'format': str(os.path.splitext(file_path)[1][1:]),
                    'frame_rate': float(stream.average_rate or 0)
                }
                
        except Exception as e:
            print(f"获取视频信息失败: {str(e)}")
            return default_info 