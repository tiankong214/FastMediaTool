from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                            QFileDialog, QProgressBar, QComboBox, QHBoxLayout, QLineEdit, QMessageBox, QFrame, QWidget, QApplication)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer, QDateTime, QProcess
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QImage, QPixmap, QMouseEvent
import os
from video_tools.compressor import VideoCompressor
import cv2
from .video_preview import VideoPreview
from .log_widget import LogWidget
import re
import time

class CompressWorker(QThread):
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(bool, str, float)
    
    def __init__(self, input_path, output_path, resolution):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.resolution = resolution
        self.is_cancelled = False
        self.process = None
        self.duration = None
        self.start_time = None
    
    def run(self):
        try:
            self.start_time = time.time()  # 记录开始时间
            output_resolution = VideoCompressor.parse_resolution(self.resolution)
            
            # 构建FFmpeg命令
            command = [
                'ffmpeg', '-y',
                '-hide_banner',
                '-loglevel', 'info',
                '-i', self.input_path,
                '-c:v', 'h264_nvenc' if VideoCompressor.has_nvidia_gpu() else 'libx264',
                '-preset', 'p4' if VideoCompressor.has_nvidia_gpu() else 'fast',
                '-crf', '23',
                '-b:v', '0',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-movflags', '+faststart',
            ]
            
            if output_resolution:
                command.extend([
                    '-vf', f'scale={output_resolution[0]}:{output_resolution[1]}'
                ])
            
            command.append(self.output_path)
            
            # 创建 QProcess
            self.process = QProcess()
            self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            self.process.readyReadStandardOutput.connect(self.handle_output)
            self.process.finished.connect(self.handle_finished)
            
            # 启动进程
            self.process.start(command[0], command[1:])
            
            # 等待进程完成
            self.process.waitForFinished(-1)
            
        except Exception as e:
            self.finished.emit(False, str(e), 0)
    
    def handle_output(self):
        """处理FFmpeg输出"""
        try:
            data = self.process.readAllStandardOutput().data().decode('utf-8', errors='replace')
            for line in data.splitlines():
                # 解析时长信息
                if not self.duration and "Duration:" in line:
                    duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})", line)
                    if duration_match:
                        h, m, s = map(int, duration_match.groups())
                        self.duration = h * 3600 + m * 60 + s
                
                # 解析进度信息
                time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})", line)
                if time_match and self.duration:
                    h, m, s = map(int, time_match.groups())
                    time_processed = h * 3600 + m * 60 + s
                    progress = int((time_processed / self.duration) * 100)
                    self.progress_updated.emit(progress)
                    
        except Exception as e:
            print(f"处理输出错误: {str(e)}")
    
    def handle_finished(self, exit_code, exit_status):
        """处理进程完成"""
        elapsed_time = time.time() - self.start_time  # 计算用时
        if self.is_cancelled:
            self.finished.emit(False, "已取消压缩", elapsed_time)
        elif exit_code == 0:
            self.finished.emit(True, "", elapsed_time)
        else:
            self.finished.emit(False, f"FFmpeg处理失败 (退出码: {exit_code})", elapsed_time)
    
    def cancel(self):
        """取消压缩"""
        self.is_cancelled = True
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()

class CompressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("音视频处理工作台 - 视频压缩")  # 修改标题顺序
        self.setMinimumSize(800, 450)  # 再减小50px
        
        # 设置窗口图标
        if QApplication.instance().windowIcon():
            self.setWindowIcon(QApplication.instance().windowIcon())
        
        # 添加进程变量
        self.process = None
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(2)  # 更小的间距
        layout.setContentsMargins(6, 6, 6, 6)  # 更小的边距
        
        # 创建左右布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(6)  # 更小的左右间距
        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(2)
        
        # 添加视频预览
        self.preview = VideoPreview()
        self.preview.setStyleSheet("""
            VideoPreview {
                background-color: #e0e0e0;
                border: 2px dashed #999;
                border-radius: 5px;
                padding: 20px;
            }
        """)
        left_layout.addWidget(self.preview)
        
        # 添加文件信息标签
        info_style = """
            QLabel {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 6px;
                min-height: 90px;
            }
        """
        
        # 原始文件信息
        self.original_info_label = QLabel("原始文件信息：\n\n请选择或拖放视频文件")
        self.original_info_label.setStyleSheet(info_style)
        self.original_info_label.setWordWrap(True)  # 允许文本换行
        right_layout.addWidget(self.original_info_label)
        
        # 压缩文件信息
        self.compressed_info_label = QLabel("压缩文件信息：\n\n等待压缩...")
        self.compressed_info_label.setStyleSheet(info_style)
        self.compressed_info_label.setWordWrap(True)  # 允许文本换行
        right_layout.addWidget(self.compressed_info_label)
        
        # 将左右布局添加到内容布局
        content_layout.addLayout(left_layout, 1)
        content_layout.addLayout(right_layout, 1)
        
        # 将内容布局添加到主布局
        layout.addLayout(content_layout)
        
        # 添加日志组件
        self.log_widget = LogWidget()
        layout.addWidget(self.log_widget)
        
        # 调整日志组件高度
        self.log_widget.setFixedHeight(150)
        
        # 进度条和设置区域使用更紧凑的布局
        settings_container = QWidget()
        settings_container_layout = QVBoxLayout(settings_container)
        settings_container_layout.setSpacing(2)
        settings_container_layout.setContentsMargins(0, 2, 0, 2)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")  # 显示百分比
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #999;
                border-radius: 3px;
                text-align: center;
                height: 14px;
            }
            QProgressBar::chunk {
                background-color: #4682B4;
                border-radius: 2px;
            }
        """)
        settings_container_layout.addWidget(self.progress)
        
        # 输出目录选择
        output_dir_layout = QHBoxLayout()
        output_dir_layout.setSpacing(4)
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("请选择输出目录...")
        self.output_dir_edit.setText("")  # 确保初始为空
        
        self.output_dir_button = QPushButton("选择目录")
        self.output_dir_button.clicked.connect(self.select_output_dir)
        self.output_dir_button.setEnabled(True)  # 始终启用目录选择按钮
        
        output_dir_layout.addWidget(QLabel("输出目录:"))
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(self.output_dir_button)
        
        settings_container_layout.addLayout(output_dir_layout)
        
        # 分辨率和格式设置
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(5)
        
        # 分辨率选择
        self.resolution_combo = QComboBox()
        resolutions = [
            "原始分辨率",
            "4K (3840×2160) - 超高清",
            "2K (2560×1440) - QHD",
            "1080P (1920×1080) - 全高清",
            "720P (1280×720) - 高清",
            "480P (854×480) - 标清",
            "360P (640×360) - 流畅"
        ]
        self.resolution_combo.addItems(resolutions)
        # 设置默认选项为1080P
        self.resolution_combo.setCurrentText("1080P (1920×1080) - 全高清")
        settings_layout.addWidget(QLabel("输出分辨率："))
        settings_layout.addWidget(self.resolution_combo)
        
        # 输出格式
        settings_layout.addWidget(QLabel("输出格式：MP4"))
        
        settings_container_layout.addLayout(settings_layout)
        
        # 添加设置容器到主布局
        layout.addWidget(settings_container)
        
        # 按钮区域使用更紧凑的布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.start_button = QPushButton("开始压缩")
        self.cancel_button = QPushButton("取消")
        self.back_button = QPushButton("返回")
        
        # 设置按钮样式
        buttons_style = """
            QPushButton {
                padding: 4px 14px;
                border-radius: 4px;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton#start_button {
                background: #4CAF50;
                color: white;
            }
            QPushButton#start_button:hover {
                background: #45a049;
            }
            QPushButton#cancel_button {
                background: #f44336;
                color: white;
            }
            QPushButton#cancel_button:hover {
                background: #da190b;
            }
            QPushButton#back_button {
                background: #9e9e9e;
                color: white;
            }
            QPushButton#back_button:hover {
                background: #7d7d7d;
            }
        """
        self.setStyleSheet(self.styleSheet() + buttons_style)
        
        # 设置按钮对象名以便应用样式
        self.start_button.setObjectName("start_button")
        self.cancel_button.setObjectName("cancel_button")
        self.back_button.setObjectName("back_button")
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.back_button)
        layout.addLayout(button_layout)
        
        # 连接信号
        self.start_button.clicked.connect(self.start_compression)
        self.cancel_button.clicked.connect(self.cancel_compress)
        self.back_button.clicked.connect(self.reject)  # 关闭对话框
        self.preview.preview_label.click_handler = self.select_file
        
        # 设置拖放
        self.setAcceptDrops(True)
        
        self.current_file = None
        self.compress_worker = None
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.process_video_file(files[0])
    
    def select_file(self, event):
        """选择视频文件"""
        dialog = QFileDialog(
            self,
            "选择视频文件",
            "",
            "所有视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v *.3gp *.ts *.mts *.m2ts *.vob);;所有文件 (*.*)"
        )
        # 设置对话框大小
        dialog.resize(600, 400)
        
        # 设置中文按钮文本
        dialog.setLabelText(QFileDialog.DialogLabel.Accept, "选择")
        dialog.setLabelText(QFileDialog.DialogLabel.Reject, "取消")
        dialog.setLabelText(QFileDialog.DialogLabel.LookIn, "查看")
        dialog.setLabelText(QFileDialog.DialogLabel.FileName, "文件名")
        dialog.setLabelText(QFileDialog.DialogLabel.FileType, "文件类型")
        
        if dialog.exec():
            file_path = dialog.selectedFiles()[0]
            self.process_video_file(file_path)
    
    def process_video_file(self, file_path):
        """处理视频文件"""
        try:
            # 验证文件
            if not os.path.exists(file_path):
                raise FileNotFoundError("文件不存在")
            
            # 获取视频信息
            info = VideoCompressor.get_video_info(file_path)
            
            # 更新UI
            self.current_file = file_path
            self.preview.load_video(file_path)
            
            # 更新原始文件信息
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # 转换为MB
            duration = int(info['duration'])
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60
            
            info_text = (
                f"原始文件信息：\n\n"
                f"分辨率：{info['width']}x{info['height']}\n"
                f"时长：{hours:02d}:{minutes:02d}:{seconds:02d}\n"
                f"大小：{file_size:.1f}MB\n"
                f"格式：{info['format']}"
            )
            self.original_info_label.setText(info_text)
            
            # 启用开始按钮
            self.start_button.setEnabled(True)
            
            # 记录日志
            self.log_widget.log(f"已选择文件：{file_path}")
            
        except Exception as e:
            self.show_error_message(f"处理文件失败：{str(e)}")
            self.current_file = None
            self.start_button.setEnabled(False)
    
    def select_output_dir(self):
        """选择输出目录"""
        try:
            # 获取初始目录
            initial_dir = ""
            if self.current_file:
                initial_dir = os.path.dirname(self.current_file)
            elif self.output_dir_edit.text():
                initial_dir = self.output_dir_edit.text()
            
            # 创建目录选择对话框
            dialog = QFileDialog(
                self,
                "选择输出目录",
                initial_dir
            )
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            dialog.setOption(QFileDialog.Option.ShowDirsOnly)
            
            # 设置对话框大小
            dialog.resize(500, 400)  # 设置更小的尺寸
            
            # 设置中文按钮文本
            dialog.setLabelText(QFileDialog.DialogLabel.Accept, "选择")
            dialog.setLabelText(QFileDialog.DialogLabel.Reject, "取消")
            dialog.setLabelText(QFileDialog.DialogLabel.LookIn, "位置")
            dialog.setLabelText(QFileDialog.DialogLabel.FileName, "文件名")
            dialog.setLabelText(QFileDialog.DialogLabel.FileType, "文件类型")
            
            if dialog.exec():
                dir_path = dialog.selectedFiles()[0]
                # 规范化路径
                dir_path = os.path.normpath(dir_path)
                self.output_dir_edit.setText(dir_path)
                self.log_widget.log(f"已选择输出目录：{dir_path}")
                
        except Exception as e:
            self.show_error_message(f"选择输出目录失败：{str(e)}")
    
    def start_compression(self):
        """开始压缩"""
        try:
            if not self.current_file:
                QMessageBox.warning(
                    self,
                    "提示",
                    "请先选择视频文件",
                    QMessageBox.StandardButton.Ok
                )
                return
            
            # 检查输出目录
            output_dir = self.output_dir_edit.text()
            if not output_dir:
                # 弹窗提示用户选择输出目录
                QMessageBox.warning(
                    self,
                    "提示",
                    "请选择输出目录",
                    QMessageBox.StandardButton.Ok
                )
                # 打开目录选择对话框
                dialog = QFileDialog(
                    self,
                    "选择输出目录",
                    os.path.dirname(self.current_file)
                )
                dialog.setFileMode(QFileDialog.FileMode.Directory)
                dialog.setOption(QFileDialog.Option.ShowDirsOnly)
                
                # 设置对话框大小
                dialog.resize(500, 400)
                
                # 设置中文按钮文本
                dialog.setLabelText(QFileDialog.DialogLabel.Accept, "选择")
                dialog.setLabelText(QFileDialog.DialogLabel.Reject, "取消")
                dialog.setLabelText(QFileDialog.DialogLabel.LookIn, "位置")
                dialog.setLabelText(QFileDialog.DialogLabel.FileName, "文件名")
                dialog.setLabelText(QFileDialog.DialogLabel.FileType, "文件类型")
                
                if dialog.exec():
                    output_dir = dialog.selectedFiles()[0]
                else:
                    return
            
            # 检查输出目录是否与输入目录相同
            input_dir = os.path.dirname(os.path.abspath(self.current_file))
            output_dir = os.path.abspath(output_dir)
            
            if input_dir == output_dir:
                QMessageBox.warning(
                    self,
                    "提示",
                    "输出目录不能与原视频目录相同，请选择其他目录",
                    QMessageBox.StandardButton.Ok
                )
                return
            
            self.output_dir_edit.setText(output_dir)
            
            # 准备输出文件路径（使用与输入文件相同的名称）
            input_filename = os.path.basename(self.current_file)
            base_name = os.path.splitext(input_filename)[0]
            output_path = os.path.join(output_dir, base_name + '.mp4')
            
            # 检查文件是否已存在
            if os.path.exists(output_path):
                msg_box = QMessageBox(
                    QMessageBox.Icon.Question,
                    "确认覆盖",
                    f"文件 {os.path.basename(output_path)} 已存在，是否覆盖？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    self
                )
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)
                
                # 设置按钮文本
                yes_button = msg_box.button(QMessageBox.StandardButton.Yes)
                no_button = msg_box.button(QMessageBox.StandardButton.No)
                yes_button.setText("是")
                no_button.setText("否")
                
                reply = msg_box.exec()
                
                if reply == QMessageBox.StandardButton.No:
                    self.log_widget.log("用户取消覆盖文件，压缩已取消", "INFO")
                    return
                
                self.log_widget.log("用户选择覆盖现有文件", "INFO")
            
            # 记录日志
            self.log_widget.log(f"输入文件：{self.current_file}")
            self.log_widget.log(f"输出目录：{output_dir}")
            self.log_widget.log(f"输出文件：{output_path}")
            
            # 禁用开始按钮，启用取消按钮
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            # 创建并启动工作线程
            self.compress_worker = CompressWorker(
                self.current_file,
                output_path,
                self.resolution_combo.currentText()
            )
            self.compress_worker.progress_updated.connect(self.update_progress)
            self.compress_worker.finished.connect(self.compression_finished)
            self.compress_worker.start()
            
        except Exception as e:
            self.show_error_message(f"压缩失败：{str(e)}")
    
    def update_progress(self, value):
        self.progress.setValue(value)
        self.log_widget.log(f"压缩进度：{value}%", "DEBUG")
    
    def compression_finished(self, success, error_message, elapsed_time):
        """压缩完成的回调"""
        try:
            # 获取输出路径（在重置 worker 之前）
            output_path = self.compress_worker.output_path
            
            # 重置工作线程
            self.compress_worker = None
            
            # 恢复按钮状态
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            
            if success:
                try:
                    # 获取压缩后的文件信息
                    compressed_info = VideoCompressor.get_video_info(output_path)
                    
                    # 格式化文件大小
                    original_size = os.path.getsize(self.current_file) / (1024 * 1024)
                    compressed_size = compressed_info['size']
                    reduction = ((original_size - compressed_size) / original_size) * 100
                    
                    # 格式化时长
                    duration = int(compressed_info['duration'])
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    seconds = duration % 60
                    
                    # 格式化用时
                    minutes = int(elapsed_time // 60)
                    seconds = int(elapsed_time % 60)
                    
                    # 更新压缩信息标签
                    info_text = (
                        f"压缩文件信息：\n\n"
                        f"分辨率：{compressed_info['width']}x{compressed_info['height']}\n"
                        f"时长：{hours:02d}:{minutes:02d}:{seconds:02d}\n"
                        f"大小：{compressed_size:.1f}MB (减小了{reduction:.1f}%)\n"
                        f"格式：{compressed_info['format']}\n"
                        f"\n压缩完成！用时：{minutes}分{seconds}秒"
                    )
                    self.compressed_info_label.setText(info_text)
                    self.show_success_message(elapsed_time)
                    
                except Exception as e:
                    self.show_error_message(f"获取压缩文件信息失败：{str(e)}")
            else:
                self.show_error_message(f"压缩失败：{error_message}")
                self.compressed_info_label.setText("压缩失败，请查看错误信息")
                
        except Exception as e:
            self.show_error_message(f"处理压缩结果失败：{str(e)}")
    
    def show_success_message(self, elapsed_time):
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        self.log_widget.log(f"压缩完成！用时：{minutes}分{seconds}秒", "INFO")
    
    def show_error_message(self, message):
        self.log_widget.log(message, "ERROR")
        self.compressed_info_label.setText(message)
    
    def cancel_compress(self):
        """取消压缩"""
        if self.compress_worker and self.compress_worker.isRunning():
            self.log_widget.log("正在取消压缩...", "WARNING")
            self.cancel_button.setEnabled(False)
            self.compress_worker.cancel()
            self.compress_worker.wait()
            self.compress_worker = None
            
            # 更新UI
            self.start_button.setEnabled(True)
            self.progress.setValue(0)
            self.log_widget.log("已取消压缩", "INFO")

    def select_output_file(self):
        """选择输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择输出文件",
            self.output_dir_edit.text(),
            "MP4视频 (*.mp4)"
        )
        if file_path:
            # 确保文件扩展名为.mp4
            if not file_path.lower().endswith('.mp4'):
                file_path += '.mp4'
            self.output_dir_edit.setText(file_path) 