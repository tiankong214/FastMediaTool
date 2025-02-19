from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                            QFileDialog, QProgressBar, QComboBox, QHBoxLayout, QLineEdit, QMessageBox, QFrame, QWidget)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer, QDateTime
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QImage, QPixmap, QMouseEvent
import os
from video_tools.compressor import VideoCompressor
import cv2
from .video_preview import VideoPreview

class CompressWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, input_path, output_path, resolution):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.resolution = resolution
        self.process = None
        self.is_cancelled = False
    
    def run(self):
        try:
            def progress_callback(p):
                if self.is_cancelled:
                    return False  # 通知压缩器停止处理
                self.progress.emit(p)
                return True
            
            success = VideoCompressor.compress_video(
                self.input_path,
                self.output_path,
                self.resolution,
                progress_callback,
                self  # 传递worker实例以便设置process
            )
            if self.is_cancelled:
                self.finished.emit(False, "已取消压缩")
                return
            self.finished.emit(success, self.output_path if success else "压缩失败")
        except Exception as e:
            self.finished.emit(False, str(e))

    def terminate(self):
        """终止压缩进程"""
        self.is_cancelled = True
        if self.process:
            print("正在终止FFmpeg进程...")
            self.process.terminate()
            self.process.wait()  # 等待进程完全终止
            print("FFmpeg进程已终止")
        super().terminate()

class CompressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("视频压缩 - 音视频处理工作台")
        self.setMinimumSize(800, 450)  # 再减小50px
        
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
        
        # 输出目录
        output_dir_layout = QHBoxLayout()
        output_dir_layout.setSpacing(5)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        self.output_dir_edit.setPlaceholderText("请先选择视频文件")
        self.output_dir_button = QPushButton("浏览")
        self.output_dir_button.clicked.connect(self.select_output_dir)
        self.output_dir_button.setEnabled(False)  # 初始状态禁用
        output_dir_layout.addWidget(QLabel("输出目录："))
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
        self.start_button.clicked.connect(self.start_compress)
        self.cancel_button.clicked.connect(self.cancel_compress)
        self.back_button.clicked.connect(self.reject)  # 关闭对话框
        self.preview.preview_label.click_handler = self.select_file
        
        # 设置拖放
        self.setAcceptDrops(True)
        
        self.current_file = None
        self.worker = None
    
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
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "所有视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v *.3gp *.ts *.mts *.m2ts *.vob);;所有文件 (*.*)"
        )
        if file_path:
            self.process_video_file(file_path)
    
    def process_video_file(self, file_path):
        """处理视频文件"""
        try:
            self.current_file = file_path
            info = VideoCompressor.get_video_info(file_path)
            
            # 加载视频预览
            self.preview.load_video(file_path)
            
            # 格式化时间
            minutes = int(info['duration'] // 60)
            seconds = int(info['duration'] % 60)
            
            self.original_info_label.setText(
                f"原始文件信息：\n"
                f"路径：{file_path}\n"
                f"分辨率：{info['width']}x{info['height']}\n"
                f"时长：{minutes:02d}:{seconds:02d}\n"
                f"大小：{info['size']:.2f}MB"
            )
            
            # 重置压缩信息
            self.compressed_info_label.setText("压缩文件信息：\n\n等待压缩...")
            
            # 设置默认输出文件名（总是使用.mp4扩展名）
            video_dir = os.path.dirname(file_path)
            video_name = os.path.splitext(os.path.basename(file_path))[0]
            default_output = os.path.join(video_dir, f"{video_name}_compressed.mp4")
            self.output_dir_edit.setText(default_output)
            
            # 启用相关控件
            self.output_dir_button.setEnabled(True)
            self.start_button.setEnabled(True)
            
        except Exception as e:
            self.original_info_label.setText(f"错误：无法读取文件信息\n{str(e)}")
            self.start_button.setEnabled(False)
            self.output_dir_edit.clear()
    
    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    
    def start_compress(self):
        if not self.current_file:
            return
        
        # 检查输出目录
        output_dir = self.output_dir_edit.text()
        if not output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return
        
        # 获取保存路径
        file_name = os.path.splitext(os.path.basename(self.current_file))[0]
        # 使用原文件名
        output_filename = f"{file_name}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        
        # 检查文件是否已存在
        if os.path.exists(output_path):
            reply = QMessageBox.question(
                self,
                "文件已存在",
                "输出文件已存在，是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        # 开始压缩
        self.progress.setValue(0)  # 重置进度条
        self.progress.setVisible(True)  # 确保进度条可见
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)  # 确保取消按钮可用
        
        self.worker = CompressWorker(
            self.current_file,
            output_path,
            self.resolution_combo.currentText()
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.compression_finished)
        self.worker.start()
    
    def update_progress(self, value):
        # 确保进度值在有效范围内
        value = max(0, min(value, 100))
        self.progress.setValue(value)
        # 强制更新UI
        self.progress.repaint()
    
    def compression_finished(self, success, message):
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        
        if success:
            try:
                # 获取原始文件信息
                original_info = VideoCompressor.get_video_info(self.current_file)
                # 获取压缩后文件信息
                compressed_info = VideoCompressor.get_video_info(message)
                
                # 计算压缩比率
                compression_ratio = round((1 - compressed_info['size'] / original_info['size']) * 100, 2)
                
                # 格式化时间
                original_minutes = int(original_info['duration'] // 60)
                original_seconds = int(original_info['duration'] % 60)
                compressed_minutes = int(compressed_info['duration'] // 60)
                compressed_seconds = int(compressed_info['duration'] % 60)
                
                # 更新信息显示
                self.original_info_label.setText(
                    f"原始文件信息：\n\n"
                    f"路径：{self.current_file}\n"
                    f"分辨率：{original_info['width']}x{original_info['height']}\n"
                    f"时长：{original_minutes:02d}:{original_seconds:02d}\n"
                    f"大小：{original_info['size']:.2f}MB"
                )
                
                self.compressed_info_label.setText(
                    f"压缩后文件信息：\n\n"
                    f"路径：{message}\n"
                    f"分辨率：{compressed_info['width']}x{compressed_info['height']}\n"
                    f"时长：{compressed_minutes:02d}:{compressed_seconds:02d}\n"
                    f"大小：{compressed_info['size']:.2f}MB\n"
                    f"压缩比率：{compression_ratio}%\n"
                    f"\n✅ 压缩完成！"
                )
            except Exception as e:
                self.compressed_info_label.setText(f"压缩完成，但无法获取详细信息：{str(e)}")
            self.progress.setValue(100)  # 确保进度条显示完成
        else:
            self.compressed_info_label.setText(f"压缩失败：{message}")
        
        # 延迟一段时间后隐藏进度条
        QTimer.singleShot(3000, lambda: self.progress.setValue(0))
    
    def cancel_compress(self):
        """取消压缩"""
        if self.worker and self.worker.isRunning():
            print("正在取消压缩...")
            self.cancel_button.setEnabled(False)  # 防止重复点击
            # 停止工作线程
            self.worker.terminate()
            self.worker.wait()
            
            # 更新UI
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            self.progress.setValue(0)
            self.original_info_label.setText(f"{self.original_info_label.text()}\n\n已取消压缩")
            self.compressed_info_label.setText(f"{self.compressed_info_label.text()}\n\n已取消压缩")
            
            # 清理临时文件
            if hasattr(self.worker, 'output_path') and os.path.exists(self.worker.output_path):
                try:
                    os.remove(self.worker.output_path)
                    print(f"已删除临时文件: {self.worker.output_path}")
                except Exception as e:
                    print(f"删除临时文件失败: {str(e)}")
                    pass

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