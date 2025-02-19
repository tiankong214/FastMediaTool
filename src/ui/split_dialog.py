from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                            QFileDialog, QProgressBar, QHBoxLayout, QLineEdit, 
                            QMessageBox, QWidget)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QImage, QPixmap, QMouseEvent
import os
from video_tools.splitter import VideoSplitter
import cv2
from .video_preview import VideoPreview

class SplitWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, input_path, output_dir):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir
        self.process = None
        self.is_cancelled = False
    
    def run(self):
        try:
            def progress_callback(p):
                if self.is_cancelled:
                    return False
                self.progress.emit(p)
                return True
            
            success = VideoSplitter.split_video(
                self.input_path,
                self.output_dir,
                progress_callback,
                self
            )
            if self.is_cancelled:
                self.finished.emit(False, "已取消分割")
                return
            self.finished.emit(success, "分割完成" if success else "分割失败")
        except Exception as e:
            self.finished.emit(False, str(e))

    def terminate(self):
        self.is_cancelled = True
        if self.process:
            print("正在终止FFmpeg进程...")
            self.process.terminate()
            self.process.wait()
            print("FFmpeg进程已终止")
        super().terminate()

class SplitDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("视频分割 - 音视频处理工作台")
        self.setMinimumSize(800, 450)
        
        # 添加进程变量
        self.process = None
        
        # 添加一个字典来跟踪已显示的文件
        self.displayed_parts = {}
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(6, 6, 6, 6)
        
        # 创建左右布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(6)
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
        self.original_info_label.setWordWrap(True)
        right_layout.addWidget(self.original_info_label)
        
        # 分割信息
        self.split_info_label = QLabel("分割信息：\n\n等待分割...")
        self.split_info_label.setStyleSheet(info_style)
        self.split_info_label.setWordWrap(True)
        right_layout.addWidget(self.split_info_label)
        
        # 将左右布局添加到内容布局
        content_layout.addLayout(left_layout, 1)
        content_layout.addLayout(right_layout, 1)
        
        # 将内容布局添加到主布局
        layout.addLayout(content_layout)
        
        # 进度条和设置区域
        settings_container = QWidget()
        settings_container_layout = QVBoxLayout(settings_container)
        settings_container_layout.setSpacing(2)
        settings_container_layout.setContentsMargins(0, 2, 0, 2)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
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
        self.output_dir_button.setEnabled(False)
        output_dir_layout.addWidget(QLabel("输出目录："))
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(self.output_dir_button)
        settings_container_layout.addLayout(output_dir_layout)
        
        # 添加设置容器到主布局
        layout.addWidget(settings_container)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.start_button = QPushButton("开始分割")
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
                border: 1px solid #45a049;
            }
            QPushButton#start_button:hover {
                background: #45a049;
                border: 1px solid #3d8b40;
            }
            QPushButton#cancel_button {
                background: #f44336;
                color: white;
                border: 1px solid #da190b;
            }
            QPushButton#cancel_button:hover {
                background: #da190b;
                border: 1px solid #c41810;
            }
            QPushButton#back_button {
                background: #9e9e9e;
                color: white;
                border: 1px solid #7d7d7d;
            }
            QPushButton#back_button:hover {
                background: #7d7d7d;
                border: 1px solid #666666;
            }
        """
        self.setStyleSheet(self.styleSheet() + buttons_style)
        
        # 设置按钮对象名
        self.start_button.setObjectName("start_button")
        self.cancel_button.setObjectName("cancel_button")
        self.back_button.setObjectName("back_button")
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.back_button)
        layout.addLayout(button_layout)
        
        # 连接信号
        self.start_button.clicked.connect(self.start_split)
        self.cancel_button.clicked.connect(self.cancel_split)
        self.back_button.clicked.connect(self.reject)
        self.preview.preview_label.click_handler = self.select_file
        
        # 设置拖放
        self.setAcceptDrops(True)
        
        self.current_file = None
        self.worker = None 

    def select_file(self, event):
        """选择视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov);;所有文件 (*.*)"
        )
        if file_path:
            self.process_video_file(file_path)
    
    def process_video_file(self, file_path):
        """处理视频文件"""
        try:
            self.current_file = file_path
            info = VideoSplitter.get_video_info(file_path)
            
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
            
            # 重置分割信息
            self.split_info_label.setText("分割信息：\n\n等待分割...")
            
            # 设置输出目录为原视频所在目录
            video_dir = os.path.dirname(file_path)
            self.output_dir_edit.setText(video_dir)
            
            # 启用相关控件
            self.output_dir_button.setEnabled(True)
            self.start_button.setEnabled(True)
            
        except Exception as e:
            self.original_info_label.setText(f"错误：无法读取文件信息\n{str(e)}")
            self.start_button.setEnabled(False)
            self.output_dir_edit.clear()
    
    def select_output_dir(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    
    def start_split(self):
        """开始分割"""
        if not self.current_file:
            return
        
        # 检查输出目录
        output_dir = self.output_dir_edit.text()
        if not output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return
        
        # 重置已显示文件列表
        self.displayed_parts = {}
        
        # 开始分割
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.split_info_label.setText("分割信息：\n\n正在分析视频...")
        
        self.worker = SplitWorker(
            self.current_file,
            output_dir,
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.split_finished)
        self.worker.start()
    
    def update_progress(self, value):
        """更新进度"""
        value = max(0, min(value, 100))
        self.progress.setValue(value)
        
        # 获取输出目录中的所有分割文件
        if hasattr(self, 'output_dir_edit') and self.output_dir_edit.text() and self.current_file:
            output_dir = self.output_dir_edit.text()
            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            info_text = "分割信息：\n\n"
            
            # 检查新生成的文件
            for f in os.listdir(output_dir):
                # 检查文件名是否匹配原文件名加序号的模式
                if f.startswith(f"{base_name}_") and f.endswith(".mp4"):
                    file_path = os.path.join(output_dir, f)
                    
                    # 如果这个文件还没有显示过
                    if f not in self.displayed_parts:
                        try:
                            # 获取视频信息
                            cap = cv2.VideoCapture(file_path)
                            if cap.isOpened():
                                fps = cap.get(cv2.CAP_PROP_FPS)
                                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                                duration = total_frames / fps if fps > 0 else 0
                                cap.release()
                                
                                # 获取文件大小
                                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                                
                                # 保存到已显示文件字典中
                                self.displayed_parts[f] = {
                                    'duration': duration,
                                    'size': size_mb
                                }
                        except Exception as e:
                            print(f"获取文件信息失败: {str(e)}")
            
            # 按文件名排序并显示所有已处理的文件
            for f in sorted(self.displayed_parts.keys()):
                part = self.displayed_parts[f]
                info_text += f"{f} - {part['duration']:.1f}秒 - {part['size']:.2f}MB\n"
            
            if value < 100:
                info_text += "\n正在分割..."
            
            self.split_info_label.setText(info_text)
        
        self.progress.repaint()
    
    def split_finished(self, success, message):
        """分割完成回调"""
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if success:
            # 更新一次进度信息以显示最终结果
            self.update_progress(100)
        else:
            self.split_info_label.setText(f"分割失败：{message}")
        
        QTimer.singleShot(3000, lambda: self.progress.setValue(0))
    
    def cancel_split(self):
        """取消分割"""
        if self.worker and self.worker.isRunning():
            print("正在取消分割...")
            self.cancel_button.setEnabled(False)
            self.worker.terminate()
            self.worker.wait()
            
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            self.progress.setValue(0)
            self.split_info_label.setText("分割信息：\n\n已取消分割")

    def dragEnterEvent(self, event: QDragEnterEvent):
        """处理拖入事件"""
        if event.mimeData().hasUrls():
            # 检查是否是视频文件
            file_path = event.mimeData().urls()[0].toLocalFile()
            if file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                event.accept()
                return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        """处理放下事件"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.process_video_file(files[0]) 