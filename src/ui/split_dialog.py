from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                            QFileDialog, QProgressBar, QHBoxLayout, QLineEdit, 
                            QMessageBox, QWidget, QApplication)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QMimeData, QUrl
from PyQt6.QtGui import (QDragEnterEvent, QDropEvent, QImage, QPixmap, 
                        QMouseEvent, QIcon)
import os
from typing import Optional, Callable, Dict, List, cast

from video_tools.video_splitter import VideoSplitter
from .video_preview import VideoPreview
from .log_widget import LogWidget

class SplitWorker(QThread):
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, input_path: str, output_dir: str):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir
        self.is_cancelled = False
    
    def run(self):
        try:
            success = VideoSplitter.split_video(
                input_path=self.input_path,
                output_dir=self.output_dir,
                progress_callback=self.update_progress,
                worker=self
            )
            self.finished.emit(success, "" if success else "分割失败")
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def update_progress(self, value: int) -> bool:
        if self.is_cancelled:
            return False
        self.progress_updated.emit(value)
        return True
    
    def cancel(self):
        self.is_cancelled = True
    
    def log(self, message: str, level: str = "INFO"):
        """添加日志方法"""
        print(f"[{level}] {message}")

class SplitDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("音视频处理工作台 - 视频分割")
        self.setMinimumSize(800, 450)
        
        # 设置窗口图标
        app = cast(QApplication, QApplication.instance())
        if app and app.windowIcon():
            self.setWindowIcon(app.windowIcon())
        
        # 初始化成员变量
        self.current_file: Optional[str] = None
        self.split_worker: Optional[SplitWorker] = None
        self.output_dir_edit: QLineEdit = QLineEdit()
        
        # 创建UI组件
        self._create_ui()
        
    def _create_ui(self):
        """创建UI组件"""
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
        
        # 添加日志组件
        self.log_widget = LogWidget()
        layout.addWidget(self.log_widget)
        self.log_widget.setFixedHeight(150)
        
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
        layout.addWidget(self.progress)
        
        # 添加输出目录选择
        output_dir_layout = QHBoxLayout()
        output_dir_label = QLabel("输出目录:")
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("选择输出目录")
        self.output_dir_button = QPushButton("浏览")
        self.output_dir_button.clicked.connect(self.select_output_dir)
        
        output_dir_layout.addWidget(output_dir_label)
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(self.output_dir_button)
        layout.addLayout(output_dir_layout)
        
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
        
        # 初始化状态
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        # 设置拖放
        self.setAcceptDrops(True)
    
    def select_file(self, event: QMouseEvent) -> None:
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
            self.log_widget.log(f"正在处理文件：{file_path}", "INFO")
            
            info = VideoSplitter.get_video_info(file_path)
            self.preview.load_video(file_path)
            
            # 更新文件信息
            duration = float(info['duration'])  # 确保是浮点数
            minutes = int(duration // 60)  # 先转换为浮点数再做除法
            seconds = int(duration % 60)
            
            self.original_info_label.setText(
                f"原始文件信息：\n"
                f"路径：{file_path}\n"
                f"分辨率：{info['width']}x{info['height']}\n"
                f"时长：{minutes:02d}:{seconds:02d}\n"
                f"大小：{float(info['size']):.2f}MB"
            )
            
            self.split_info_label.setText("分割信息：\n\n等待分割...")
            self.start_button.setEnabled(True)
            
        except Exception as e:
            self.log_widget.log(f"处理文件失败：{str(e)}", "ERROR")
            self.start_button.setEnabled(False)
    
    def start_split(self):
        """开始分割"""
        try:
            if not self.current_file:
                self.log_widget.log("请先选择视频文件", "WARNING")
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
                self.log_widget.log("请选择输出目录", "WARNING")
                # 添加弹窗提示
                msg_box = QMessageBox(
                    QMessageBox.Icon.Warning,
                    "提示",
                    "请先选择输出目录",
                    QMessageBox.StandardButton.Ok,
                    self
                )
                # 设置按钮文本
                ok_button = msg_box.button(QMessageBox.StandardButton.Ok)
                ok_button.setText("确定")
                msg_box.exec()
                return
            
            # 禁用开始按钮，启用取消按钮
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            # 创建并启动工作线程
            self.split_worker = SplitWorker(
                self.current_file,
                output_dir
            )
            self.split_worker.progress_updated.connect(self.update_progress)
            self.split_worker.finished.connect(self.split_finished)
            self.split_worker.start()
            
        except Exception as e:
            self.log_widget.log(f"分割失败：{str(e)}", "ERROR")
    
    def update_progress(self, value):
        """更新进度"""
        self.progress.setValue(value)
        self.log_widget.log(f"分割进度：{value}%", "DEBUG")
        self.update_split_info(value)
    
    def split_finished(self, success, error_message):
        """分割完成的回调"""
        # 重置工作线程
        self.split_worker = None
        
        # 恢复按钮状态
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if success:
            self.show_success_message()
            self.update_split_info(100)
        else:
            self.show_error_message(f"分割失败：{error_message}")
    
    def cancel_split(self):
        """取消分割"""
        if self.split_worker and self.split_worker.isRunning():
            self.log_widget.log("正在取消分割...", "WARNING")
            self.cancel_button.setEnabled(False)
            self.split_worker.cancel()
            self.split_worker.wait()
            self.split_worker = None
            
            # 更新UI
            self.start_button.setEnabled(True)
            self.progress.setValue(0)
            self.log_widget.log("已取消分割", "INFO")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """处理拖入事件"""
        mime_data = cast(QMimeData, event.mimeData())
        if mime_data and mime_data.hasUrls():
            # 检查是否是视频文件
            urls = cast(List[QUrl], mime_data.urls())
            if urls:
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                    event.accept()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """处理放下事件"""
        mime_data = cast(QMimeData, event.mimeData())
        if mime_data and mime_data.hasUrls():
            urls = cast(List[QUrl], mime_data.urls())
            files = [u.toLocalFile() for u in urls]
            if files:
                self.process_video_file(files[0])

    def show_error_message(self, message: str) -> None:
        """显示错误消息"""
        self.log_widget.log(message, "ERROR")
    
    def show_success_message(self) -> None:
        """显示成功消息"""
        self.log_widget.log("分割完成", "INFO")
    
    def update_split_info(self, progress: int) -> None:
        """更新分割信息"""
        if not self.current_file or not self.output_dir_edit.text():
            return
        
        try:
            # 获取输出目录中的分割文件
            output_dir = self.output_dir_edit.text()
            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            split_files = [f for f in os.listdir(output_dir) 
                         if f.startswith(base_name) and f.endswith('.mp4')
                         and f != os.path.basename(self.current_file)]  # 排除原视频
            split_files.sort()  # 按文件名排序
            
            text = "分割信息：\n\n"
            
            if split_files:
                for file_name in split_files:
                    file_path = os.path.join(output_dir, file_name)
                    info = VideoSplitter.get_video_info(file_path)
                    size_mb = float(info['size'])
                    text += f"{file_name}  {info['width']}x{info['height']}  {size_mb:.1f}MB\n"
            
            text += f"\n当前进度：{progress}%"
            self.split_info_label.setText(text)
            
        except Exception as e:
            self.log_widget.log(f"更新分割信息失败: {str(e)}", "ERROR")

    def select_output_dir(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            os.path.dirname(self.current_file) if self.current_file else ""
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path) 