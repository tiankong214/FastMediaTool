from PyQt6 import QtWidgets
from PyQt6.QtWidgets import (QLabel, QHBoxLayout, QVBoxLayout, QWidget, 
                            QPushButton, QSlider, QStyle, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainter, QIcon, QColor, QMouseEvent
import cv2

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.click_handler = None

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        if self.click_handler:
            self.click_handler(ev)
        else:
            super().mousePressEvent(ev)

class VideoPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.is_playing = False
        self.total_frames = 0
        self.current_frame = 0
        self.show_placeholder()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建一个容器来包含预览标签，以便更好地控制布局
        self.preview_container = QWidget()
        # 设置固定宽度，高度按16:9比例计算
        preview_width = 480  # 减小宽度
        preview_height = int(preview_width * 9 / 16)
        self.preview_container.setFixedSize(preview_width, preview_height)
        self.preview_container.setStyleSheet("""
            QWidget {
                background-color: #000;
                border-radius: 5px;
            }
        """)
        # 使用QVBoxLayout并设置边距为0
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)
        
        # 预览区域
        self.preview_label = ClickableLabel()
        self.preview_label.setFixedSize(preview_width, preview_height)
        self.preview_label.setStyleSheet("""
            QLabel {
                color: #fff;
                font-size: 14px;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        
        # 控制栏
        control_widget = QWidget()
        control_widget.setFixedWidth(preview_width)  # 控制栏宽度与视频相同
        control_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.7);
                border-bottom-left-radius: 5px;
                border-bottom-right-radius: 5px;
            }
            QPushButton {
                border: none;
                padding: 5px;
                color: white;
                background: transparent;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 4px;
                background: #cccccc;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: white;
                border: 1px solid #999999;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QLabel {
                color: white;
            }
        """)
        
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(10, 5, 10, 5)
        
        # 播放/暂停按钮
        self.play_button = QPushButton()
        # 设置图标颜色为白色
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        pixmap = icon.pixmap(24, 24)  # 设置图标大小
        # 创建一个画家来修改图标颜色
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(255, 255, 255))  # 白色
        painter.end()
        self.play_button.setIcon(QIcon(pixmap))
        self.play_button.setFixedSize(32, 32)  # 设置按钮大小
        self.play_button.clicked.connect(self.toggle_play)
        self.play_button.setEnabled(False)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setEnabled(False)
        self.progress_slider.sliderMoved.connect(self.seek)
        
        # 时间标签
        self.time_label = QLabel("00:00 / 00:00")
        
        control_layout.addWidget(self.play_button)
        control_layout.addWidget(self.progress_slider)
        control_layout.addWidget(self.time_label)
        
        # 创建一个垂直布局来包含预览容器和控制栏
        container = QWidget()
        container.setFixedWidth(preview_width)
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(0)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.preview_container)
        container_layout.addWidget(control_widget)
        
        # 将容器添加到主布局并居中
        main_layout.addWidget(container, 0, Qt.AlignmentFlag.AlignCenter)
    
    def show_placeholder(self):
        """显示占位提示文本"""
        self.preview_label.clear()  # 清除现有的pixmap
        self.preview_label.setText("将视频文件拖至此处\n或点击选择文件")
    
    def load_video(self, file_path):
        if self.cap is not None:
            self.stop()
            self.cap.release()
        
        self.cap = cv2.VideoCapture(file_path)
        if self.cap.isOpened():
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.duration = self.total_frames / self.fps
            
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(frame)
                self.play_button.setEnabled(True)
                self.progress_slider.setEnabled(True)
                self.progress_slider.setRange(0, self.total_frames)
                self.update_time_label()
        else:
            self.show_placeholder()
    
    def display_frame(self, frame):
        # 清除文本
        self.preview_label.clear()
        
        # 调整帧大小以适应预览区域
        height, width = frame.shape[:2]
        preview_size = self.preview_container.size()
        scale = min(preview_size.width() / width, preview_size.height() / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        frame = cv2.resize(frame, (new_width, new_height))
        
        # 转换颜色空间
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = QImage(frame.data, frame.shape[1], frame.shape[0], 
                      frame.strides[0], QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.preview_label.setPixmap(pixmap)
        # 确保预览标签大小与图像一致
        self.preview_label.setFixedSize(new_width, new_height)
    
    def update_time_label(self):
        current_time = self.current_frame / self.fps if self.fps else 0
        total_time = self.duration if hasattr(self, 'duration') else 0
        self.time_label.setText(f"{self.format_time(current_time)} / {self.format_time(total_time)}")
    
    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def seek(self, frame_no):
        if self.cap is not None and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            self.current_frame = frame_no
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(frame)
                self.update_time_label()
    
    def update_frame(self):
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(frame)
                self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                self.progress_slider.setValue(self.current_frame)
                self.update_time_label()
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.current_frame = 0
                self.progress_slider.setValue(0)
                self.stop()
    
    def toggle_play(self):
        if self.is_playing:
            self.stop()
        else:
            self.play()
    
    def play(self):
        if self.cap is not None and self.cap.isOpened():
            self.timer.start(int(1000/self.fps))  # 使用实际的帧率
            self.is_playing = True
            # 设置暂停图标（白色）
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
            pixmap = icon.pixmap(24, 24)
            painter = QPainter(pixmap)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), QColor(255, 255, 255))
            painter.end()
            self.play_button.setIcon(QIcon(pixmap))
    
    def stop(self):
        self.timer.stop()
        self.is_playing = False
        # 设置播放图标（白色）
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        pixmap = icon.pixmap(24, 24)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(255, 255, 255))
        painter.end()
        self.play_button.setIcon(QIcon(pixmap))
    
    def closeEvent(self, event):
        self.stop()
        if self.cap is not None:
            self.cap.release()
        super().closeEvent(event)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 不需要在这里调整大小，因为已经固定了尺寸 