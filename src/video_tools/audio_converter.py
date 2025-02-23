import av
import os
from typing import Dict, Callable, Any, cast, List
from av.audio.stream import AudioStream
from av.audio.frame import AudioFrame
from av.container import Container, InputContainer, OutputContainer
from av.packet import Packet

class AudioConverter:
    @staticmethod
    def convert_audio(input_path: str, output_path: str, format: str,
                     progress_callback: Callable[[int], bool], worker: Any = None) -> bool:
        """转换音频格式"""
        output_container: OutputContainer | None = None
        try:
            # 打开输入文件
            input_container = cast(InputContainer, av.open(input_path))
            
            # 获取音频流
            in_audio_stream = cast(AudioStream, input_container.streams.audio[0])
            
            # 创建输出容器
            output_container = cast(OutputContainer, av.open(output_path, 'w'))
            
            # 添加音频流并设置参数
            audio_stream = cast(AudioStream, output_container.add_stream(format, options={
                'b:a': '128k',  # 比特率
                'ar': str(in_audio_stream.rate),  # 采样率
                'ac': str(in_audio_stream.channels),  # 声道数
            }))
            
            # 处理每一帧
            total_frames = float(in_audio_stream.frames or 1000)  # 如果未知则估计
            frame_count = 0
            
            # 处理音频帧
            for frame in input_container.decode(audio=0):
                frame = cast(AudioFrame, frame)
                # 编码音频帧
                packets: List[Packet] = []
                try:
                    packets = audio_stream.encode(frame)
                except TypeError:
                    # 如果直接编码失败，创建新的音频帧
                    array = frame.to_ndarray()
                    new_frame = AudioFrame.from_ndarray(
                        array,
                        layout=str(frame.layout),
                        format=str(frame.format)
                    )
                    new_frame.pts = frame.pts
                    new_frame.time_base = frame.time_base
                    packets = audio_stream.encode(new_frame)
                
                for packet in packets:
                    output_container.mux(packet)
                
                # 更新进度
                frame_count += 1
                progress = int((frame_count / total_frames) * 100)
                if not progress_callback(progress):
                    if output_container:
                        output_container.close()
                    return False
            
            # 刷新缓冲区
            packets = audio_stream.encode(None)
            for packet in packets:
                output_container.mux(packet)
            
            # 关闭输出容器
            output_container.close()
            
            if worker:
                worker.log("音频转换完成", "INFO")
            return True
            
        except Exception as e:
            if worker:
                worker.log(f"音频转换失败: {str(e)}", "ERROR")
            if output_container:
                output_container.close()
            return False

    @staticmethod
    def get_audio_info(file_path: str) -> Dict:
        """获取音频信息"""
        try:
            container = cast(InputContainer, av.open(file_path))
            stream = cast(AudioStream, container.streams.audio[0])
            
            info = {
                'duration': float(container.duration) / av.time_base if container.duration else 0,
                'size': os.path.getsize(file_path) / (1024 * 1024),  # MB
                'format': os.path.splitext(file_path)[1][1:],
                'sample_rate': stream.rate,
                'channels': stream.channels,
                'bit_rate': stream.bit_rate
            }
            
            container.close()
            return info
            
        except Exception as e:
            return {
                'duration': 0,
                'size': 0,
                'format': '',
                'sample_rate': None,
                'channels': None,
                'bit_rate': None
            } 