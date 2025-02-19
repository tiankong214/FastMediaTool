import os
import cv2
import subprocess
import time
from typing import List, Callable, Any
from math import ceil

class VideoSplitter:
    MIN_SIZE = 45  # MB，最小目标大小
    MAX_SIZE = 50  # MB，最大限制
    TIMEOUT = 10   # 命令执行超时时间（秒）

    @staticmethod
    def get_video_info(video_path: str) -> dict:
        """获取视频信息"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("无法打开视频文件")
        
        # 获取视频基本信息
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # 获取文件大小（MB）
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        
        cap.release()
        
        return {
            'width': width,
            'height': height,
            'fps': fps,
            'duration': duration,
            'total_frames': total_frames,
            'size': size_mb,
            'bitrate': (size_mb * 1024 * 1024 * 8) / duration if duration > 0 else 0  # bits per second
        }

    @staticmethod
    def estimate_split_point(total_size: float, total_duration: float, target_size: float) -> float:
        """估算分割点"""
        # 根据文件大小比例估算时间点
        ratio = target_size / total_size
        return total_duration * ratio

    @staticmethod
    def execute_ffmpeg(command: List[str], timeout: int = TIMEOUT) -> tuple[bool, float]:
        """
        执行FFmpeg命令并返回结果
        返回：(是否成功, 文件大小MB)
        """
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待进程完成，带超时
            start_time = time.time()
            while process.poll() is None:
                if time.time() - start_time > timeout:
                    process.terminate()
                    process.wait()
                    print("命令执行超时")
                    return False, 0
                time.sleep(0.1)
            
            # 检查输出文件
            output_path = command[-1]
            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                return True, size_mb
            return False, 0
            
        except Exception as e:
            print(f"执行命令出错: {str(e)}")
            return False, 0

    @staticmethod
    def find_split_point(input_path: str, start_time: float, end_time: float, total_size: float) -> tuple[float, float]:
        """
        使用改进的二分查找找到合适的分割点
        """
        try:
            # 首先估算一个可能的分割点
            estimated_time = VideoSplitter.estimate_split_point(
                total_size,
                end_time - start_time,
                VideoSplitter.MIN_SIZE
            ) + start_time
            
            print(f"估算分割点：{estimated_time:.2f}s")
            
            # 在估算点附近搜索
            left = max(start_time, estimated_time - 10)
            right = min(end_time, estimated_time + 10)
            best_time = start_time
            best_size = 0
            
            while right - left > 0.5:  # 精确到0.5秒
                mid = (left + right) / 2
                duration = mid - start_time
                
                # 测试当前时间点
                temp_output = "temp_test.mp4"
                command = [
                    'ffmpeg', '-y',
                    '-i', input_path,
                    '-ss', str(start_time),
                    '-t', str(duration),
                    '-c', 'copy',
                    temp_output
                ]
                
                print(f"测试时间点：{mid:.2f}s")
                success, size_mb = VideoSplitter.execute_ffmpeg(command)
                
                if success:
                    print(f"分段大小：{size_mb:.2f}MB")
                    
                    if size_mb <= VideoSplitter.MAX_SIZE:
                        if size_mb > best_size:
                            best_size = size_mb
                            best_time = mid
                        if size_mb < VideoSplitter.MIN_SIZE:
                            left = mid
                        else:
                            right = mid
                    else:
                        right = mid
                else:
                    print("测试失败，缩小范围")
                    right = mid
                
                # 清理临时文件
                if os.path.exists(temp_output):
                    os.remove(temp_output)
            
            print(f"找到分割点：{best_time:.2f}s，大小：{best_size:.2f}MB")
            return best_time, best_size
            
        except Exception as e:
            print(f"查找分割点时出错: {str(e)}")
            return start_time + 1, 0

    @staticmethod
    def get_keyframes(input_path: str) -> List[float]:
        """获取视频的关键帧时间点列表"""
        try:
            command = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'packet=pts_time,flags',
                '-of', 'csv=print_section=0',
                input_path
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            keyframes = []
            
            for line in result.stdout.splitlines():
                if line.strip():
                    pts_time, flags = line.split(',')
                    if 'K' in flags:  # 关键帧
                        keyframes.append(float(pts_time))
            
            return sorted(keyframes)
            
        except Exception as e:
            print(f"获取关键帧失败: {str(e)}")
            return []

    @staticmethod
    def find_nearest_keyframe(target_time: float, keyframes: List[float]) -> float:
        """找到最接近目标时间的关键帧"""
        return min(keyframes, key=lambda x: abs(x - target_time))

    @staticmethod
    def execute_ffmpeg_with_timeout(command: List[str], timeout: int = 30) -> bool:
        """执行FFmpeg命令，带超时控制"""
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            start_time = time.time()
            while process.poll() is None:
                if time.time() - start_time > timeout:
                    process.terminate()
                    process.wait()
                    print(f"FFmpeg命令执行超时（{timeout}秒）")
                    return False
                
                # 读取输出，防止缓冲区满
                if process.stderr:
                    line = process.stderr.readline()
                    if line:
                        print(f"FFmpeg: {line.strip()}")
                
                time.sleep(0.1)
            
            return process.returncode == 0
            
        except Exception as e:
            print(f"执行FFmpeg命令出错: {str(e)}")
            return False

    @staticmethod
    def find_next_frame_time(input_path: str, start_time: float) -> float:
        """获取下一帧的时间点"""
        try:
            command = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'packet=pts_time',
                '-read_intervals', f'{start_time}%+1',  # 只读取start_time之后的一帧
                '-of', 'csv=print_section=0',
                input_path
            ]
            
            result = subprocess.run(command, capture_output=True, text=True)
            frames = [float(t) for t in result.stdout.splitlines() if t.strip()]
            return frames[1] if len(frames) > 1 else start_time + 0.04  # 如果获取失败，假设帧间隔为0.04秒
            
        except Exception as e:
            print(f"获取下一帧时间失败: {str(e)}")
            return start_time + 0.04

    @staticmethod
    def optimize_split_point(input_path: str, keyframe_time: float, target_size: float) -> tuple[float, float]:
        """
        从关键帧开始，通过逐帧增加来找到最佳分割点
        返回：(最佳分割时间, 文件大小)
        """
        try:
            current_time = keyframe_time
            best_time = keyframe_time
            best_size = 0
            
            while True:
                # 测试当前时间点
                command = [
                    'ffmpeg', '-y',
                    '-i', input_path,
                    '-ss', '0',
                    '-t', str(current_time),
                    '-c', 'copy',
                    'temp_test.mp4'
                ]
                
                success, size_mb = VideoSplitter.execute_ffmpeg(command)
                if not success:
                    break
                
                print(f"测试时间点：{current_time:.3f}s，大小：{size_mb:.2f}MB")
                
                if size_mb > VideoSplitter.MAX_SIZE:
                    break
                
                best_time = current_time
                best_size = size_mb
                
                if size_mb >= VideoSplitter.MIN_SIZE:
                    # 如果已经达到最小目标，再尝试增加一帧
                    next_time = VideoSplitter.find_next_frame_time(input_path, current_time)
                    if next_time <= current_time:
                        break
                    
                    # 测试增加一帧后的大小
                    command[-2] = str(next_time)
                    success, next_size = VideoSplitter.execute_ffmpeg(command)
                    if not success or next_size > VideoSplitter.MAX_SIZE:
                        break
                    
                    # 如果增加一帧后仍然不超过最大限制，更新最佳点
                    best_time = next_time
                    best_size = next_size
                    break
                
                # 继续增加帧
                current_time = VideoSplitter.find_next_frame_time(input_path, current_time)
                if current_time <= best_time:
                    break
            
            # 清理临时文件
            if os.path.exists('temp_test.mp4'):
                os.remove('temp_test.mp4')
            
            return best_time, best_size
            
        except Exception as e:
            print(f"优化分割点时出错: {str(e)}")
            return keyframe_time, 0

    @staticmethod
    def get_segment_info(input_path: str, start_time: float, duration: float) -> tuple[bool, float]:
        """获取指定时间段的视频信息"""
        try:
            temp_output = "temp_segment.mp4"
            command = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c', 'copy',
                temp_output
            ]
            
            process = subprocess.run(command, capture_output=True)
            if os.path.exists(temp_output):
                size_mb = os.path.getsize(temp_output) / (1024 * 1024)
                os.remove(temp_output)
                return True, size_mb
            return False, 0
            
        except Exception as e:
            print(f"获取分段信息失败: {str(e)}")
            return False, 0

    @staticmethod
    def split_video(input_path: str, output_dir: str,
                   progress_callback: Callable[[int], bool], worker: Any = None) -> bool:
        """按文件大小分割视频"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # 获取原视频文件名（不含扩展名）
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            
            info = VideoSplitter.get_video_info(input_path)
            total_duration = info['duration']
            total_size = info['size']
            
            print(f"视频总时长：{total_duration:.2f}秒，总大小：{total_size:.2f}MB")
            progress_callback(0)
            
            # 开始分割
            final_splits = [0]  # 最终的分割点
            current_time = 0
            segment_index = 1
            
            while current_time < total_duration:
                print(f"\n处理第 {segment_index} 段...")
                start_time = current_time
                test_duration = 20  # 从20秒开始测试
                
                # 如果剩余时长小于5秒，尝试合并到前一段
                remaining_duration = total_duration - start_time
                if remaining_duration < 5 and len(final_splits) > 1:
                    # 测试合并到前一段
                    prev_start = final_splits[-2]
                    total_duration_test = total_duration - prev_start
                    success, merged_size = VideoSplitter.get_segment_info(
                        input_path, prev_start, total_duration_test
                    )
                    
                    if success and merged_size <= VideoSplitter.MAX_SIZE:
                        print(f"最后 {remaining_duration:.2f} 秒可以合并到前一段")
                        print(f"合并后大小：{merged_size:.2f}MB")
                        final_splits[-1] = total_duration
                        break
                
                # 获取初始段大小
                success, current_size = VideoSplitter.get_segment_info(
                    input_path, start_time, test_duration
                )
                
                if not success:
                    return False
                
                print(f"初始大小（{test_duration}秒）：{current_size:.2f}MB")
                
                # 二分查找找到接近50MB的点
                min_duration = 1
                max_duration = total_duration - start_time
                best_duration = test_duration
                best_size = current_size
                
                while max_duration - min_duration > 1:  # 精确到1秒
                    test_duration = (min_duration + max_duration) / 2
                    success, size = VideoSplitter.get_segment_info(
                        input_path, start_time, test_duration
                    )
                    
                    if not success:
                        break
                        
                    print(f"测试时长：{test_duration:.1f}秒，大小：{size:.2f}MB")
                    
                    if size <= VideoSplitter.MAX_SIZE:
                        best_duration = test_duration
                        best_size = size
                        min_duration = test_duration
                    else:
                        max_duration = test_duration
                
                # 找到最后一个不超过50MB的点
                final_duration = int(best_duration)
                
                # 如果这是最后一段，检查是否可以合并剩余部分
                if start_time + final_duration >= total_duration - 5:
                    success, final_size = VideoSplitter.get_segment_info(
                        input_path, start_time, total_duration - start_time
                    )
                    if success and final_size <= VideoSplitter.MAX_SIZE:
                        print(f"可以将剩余 {total_duration - start_time:.2f} 秒作为最后一段")
                        final_duration = total_duration - start_time
                
                success, final_size = VideoSplitter.get_segment_info(
                    input_path, start_time, final_duration
                )
                
                if not success:
                    return False
                
                print(f"最终时长：{final_duration}秒，大小：{final_size:.2f}MB")
                
                # 添加分割点
                current_time = start_time + final_duration
                final_splits.append(current_time)
                
                # 更新进度
                progress = int((current_time / total_duration) * 100)
                progress_callback(progress)
                
                segment_index += 1
            
            # 执行最终分割
            print("\n执行最终分割...")
            for i in range(len(final_splits) - 1):
                start_time = final_splits[i]
                end_time = final_splits[i + 1]
                
                # 使用原文件名加两位数字序号
                output_path = os.path.join(output_dir, f"{base_name}_{i+1:02d}.mp4")
                command = [
                    'ffmpeg', '-y',
                    '-i', input_path,
                    '-ss', str(start_time),
                    '-t', str(end_time - start_time),
                    '-c', 'copy',
                    output_path
                ]
                
                print(f"\n分割第 {i+1} 段: {start_time:.2f}s - {end_time:.2f}s")
                if not VideoSplitter.execute_ffmpeg_with_timeout(command):
                    return False
                
                if os.path.exists(output_path):
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    print(f"第 {i+1} 段完成，大小：{size_mb:.2f}MB")
            
            print("\n分割完成")
            progress_callback(100)
            return True
            
        except Exception as e:
            print(f"分割视频时出错: {str(e)}")
            progress_callback(0)
            return False 