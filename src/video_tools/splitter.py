import av
import os
from av.codec.context import CodecContext
from av.audio.stream import AudioStream
from av.video.stream import VideoStream
from av.container import InputContainer, OutputContainer
from typing import Callable, Any, Dict, Union, Tuple, cast

class VideoSplitter:
    MAX_SIZE = 50  # MB
    
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

    @staticmethod
    def split_segment(input_path: str, output_path: str, start_time: float, duration: float) -> float:
        """分割指定时长的片段并返回文件大小(MB)"""
        try:
            with av.open(input_path) as input_container:
                input_container = cast(InputContainer, input_container)
                with av.open(output_path, 'w') as output_container:
                    output_container = cast(OutputContainer, output_container)
                    
                    # 设置输出流
                    in_video_stream = cast(VideoStream, input_container.streams.video[0])
                    in_audio_stream = cast(AudioStream, next(
                        (s for s in input_container.streams if s.type == 'audio'),
                        None
                    ))
                    
                    # 配置视频编码器
                    video_stream = output_container.add_stream('h264')
                    video_stream.codec_context.framerate = in_video_stream.codec_context.framerate
                    video_stream.width = in_video_stream.width
                    video_stream.height = in_video_stream.height
                    
                    # 配置音频编码器
                    if in_audio_stream and in_audio_stream.codec_context:
                        codec_ctx = cast(CodecContext, in_audio_stream.codec_context)
                        audio_stream = output_container.add_stream('aac', options={
                            'ar': str(getattr(codec_ctx, 'sample_rate', 44100)),
                            'ac': str(getattr(codec_ctx, 'channels', 2)),
                            'b:a': '128k'
                        })
                    
                    # 设置起始时间（转换为微秒）
                    input_container.seek(int(start_time * 1000000))
                    end_time = int((start_time + duration) * 1000000)
                    
                    # 处理每一帧
                    for frame in input_container.decode():
                        # 检查是否超过结束时间
                        if frame.time > end_time:
                            break
                            
                        if isinstance(frame, av.VideoFrame):
                            # 编码视频帧
                            packet = video_stream.encode(frame)
                            if packet:
                                output_container.mux(packet)
                        
                        elif isinstance(frame, av.AudioFrame) and in_audio_stream:
                            # 编码音频帧
                            packet = audio_stream.encode(frame)
                            if packet:
                                output_container.mux(packet)
                    
                    # 刷新缓冲区
                    if video_stream:
                        packet = video_stream.encode(None)
                        if packet:
                            output_container.mux(packet)
                    if in_audio_stream:
                        packet = audio_stream.encode(None)
                        if packet:
                            output_container.mux(packet)
            
            if os.path.exists(output_path):
                return os.path.getsize(output_path) / (1024 * 1024)
            return 0
        except Exception:
            return 0

    @staticmethod
    def find_optimal_split_point(
        input_path: str,
        start_time: float,
        estimated_duration: float,
        output_dir: str,
        base_name: str,
        part_index: int,
        worker: Any = None
    ) -> Tuple[float, float]:
        """找到最优分割点
        
        通过逐秒增加时长，找到不超过50MB的最大分割点
        返回: (最优分割时长, 实际文件大小)
        """
        current_duration = float(estimated_duration)
        temp_output = os.path.join(output_dir, "temp_segment.mp4")
        
        try:
            while True:
                actual_size = VideoSplitter.split_segment(
                    input_path,
                    temp_output,
                    start_time,
                    current_duration
                )
                
                if worker:
                    worker.log(f"测试分割点: {current_duration}秒, 大小: {actual_size:.2f}MB", "DEBUG")
                
                if actual_size > VideoSplitter.MAX_SIZE:
                    # 找到超过50MB的点，回退一秒
                    current_duration -= 1.0
                    actual_size = VideoSplitter.split_segment(
                        input_path,
                        temp_output,
                        start_time,
                        current_duration
                    )
                    return current_duration, actual_size
                
                # 如果当前大小小于50MB，继续增加时长
                current_duration += 1.0
                
                # 检查是否超过预估时长的两倍
                if current_duration > estimated_duration * 2:
                    if worker:
                        worker.log("无法找到合适的分割点，使用当前大小", "WARNING")
                    return current_duration - 1.0, actual_size
                    
        finally:
            # 清理临时文件
            if os.path.exists(temp_output):
                try:
                    os.remove(temp_output)
                except:
                    pass

    @staticmethod
    def split_video(input_path: str, progress_callback: Callable[[int], bool],
                   worker: Any = None, output_dir: str | None = None) -> bool:
        """分割视频"""
        try:
            # 获取视频信息
            info = VideoSplitter.get_video_info(input_path)
            
            # 确保获取到的值是数值类型
            total_duration = float(info['duration'])  # 确保是浮点数
            total_size = float(info['size'])  # 确保是浮点数
            
            if worker:
                worker.log(f"视频总时长: {total_duration}秒", "INFO")
                worker.log(f"视频总大小: {total_size:.2f}MB", "INFO")
                worker.log(f"每秒平均大小: {total_size/total_duration:.2f}MB", "INFO")
                worker.log(f"输出目录: {output_dir}", "INFO")
            
            # 创建输出目录
            if not output_dir:
                output_dir = os.path.dirname(input_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取基础文件名（不包含扩展名）
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            
            # 初始化变量
            current_time = 0
            part_index = 1
            
            while current_time < total_duration:
                if worker:
                    worker.log(f"开始处理第 {part_index} 段", "INFO")
                
                # 计算剩余时长
                remaining_duration = total_duration - current_time
                
                # 预估当前段时长
                estimated_duration = min(
                    int(VideoSplitter.MAX_SIZE / (total_size / total_duration)),
                    remaining_duration
                )
                
                if worker:
                    worker.log(f"预估分割点: {estimated_duration}秒", "INFO")
                
                # 尝试不同的分割点
                optimal_duration = estimated_duration
                temp_path = os.path.join(output_dir, "temp.mp4")
                
                # 找到最优分割点
                optimal_duration, actual_size = VideoSplitter.find_optimal_split_point(
                    input_path, current_time, estimated_duration,
                    output_dir, base_name, part_index, worker
                )
                
                # 执行最终分割
                output_path = os.path.join(
                    output_dir,
                    f"{base_name}_{part_index:03d}.mp4"
                )
                
                if worker:
                    worker.log(f"执行分割: {current_time}s - {current_time + optimal_duration}s", "INFO")
                
                final_size = VideoSplitter.split_segment(
                    input_path, output_path,
                    current_time, optimal_duration
                )
                
                if worker:
                    worker.log(f"第 {part_index} 段完成: {final_size:.2f}MB", "INFO")
                
                # 更新进度
                progress = int((current_time + optimal_duration) / total_duration * 100)
                if not progress_callback(progress):
                    return False
                
                current_time += optimal_duration
                part_index += 1
                
                # 检查剩余部分
                remaining_duration = total_duration - current_time
                if remaining_duration > 0:
                    temp_check_path = os.path.join(output_dir, "temp_check.mp4")
                    remaining_size = VideoSplitter.split_segment(
                        input_path,
                        temp_check_path,
                        current_time,
                        remaining_duration
                    )
                    
                    if os.path.exists(temp_check_path):
                        os.remove(temp_check_path)
                    
                    if remaining_size <= VideoSplitter.MAX_SIZE:
                        if worker:
                            worker.log(f"剩余部分大小: {remaining_size:.2f}MB，作为最后一段", "INFO")
                        
                        # 分割最后一段 (使用3位序号)
                        output_path = os.path.join(
                            output_dir,
                            f"{base_name}_{part_index:03d}.mp4"
                        )
                        final_size = VideoSplitter.split_segment(
                            input_path, output_path,
                            current_time, remaining_duration
                        )
                        
                        if worker:
                            worker.log(f"最后一段完成: {final_size:.2f}MB", "INFO")
                        
                        progress_callback(100)
                        break
            
            if worker:
                worker.log(f"分割完成！共 {part_index} 个片段", "INFO")
            
            return True
            
        except Exception as e:
            if worker:
                worker.log(f"分割失败: {str(e)}", "ERROR")
            return False

    @staticmethod
    def calculate_segment_size(total_size: float, total_duration: float) -> float:
        """计算每个分段的大小"""
        try:
            return total_size / total_duration
        except (TypeError, ZeroDivisionError):
            return 0.0 