from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QPushButton, 
                             QMessageBox, QMenuBar, QMenu, QVBoxLayout, QLabel)
from PyQt6.QtGui import QColor, QPalette, QAction, QEnterEvent
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer, QEvent
from typing import cast, Optional
from ui.compress_dialog import CompressDialog
from ui.split_dialog import SplitDialog
from ui.convert_dialog import ConvertDialog

class AnimatedButton(QPushButton):
    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self._main_window = parent
    
    def enterEvent(self, event: QEnterEvent) -> None:
        """鼠标进入事件"""
        if self._main_window and isinstance(self._main_window, MainWindow):
            self._main_window.animate_button(self, -10)
        super().enterEvent(event)
    
    def leaveEvent(self, event: QEvent) -> None:
        """鼠标离开事件"""
        if self._main_window and isinstance(self._main_window, MainWindow):
            self._main_window.animate_button(self, 10)
        super().leaveEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("音视频处理工作台")
        self.setMinimumSize(800, 400)
        self.buttons = []  # 存储按钮引用
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QMenuBar {
                background-color: #f0f0f0;
                border-bottom: 1px solid #ddd;
            }
            QMenuBar::item {
                padding: 6px 10px;
                margin: 0;
            }
            QMenuBar::item:selected {
                background-color: #e0e0e0;
            }
            QMenu {
                background-color: white;
                border: 1px solid #ddd;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 30px 5px 20px;
            }
            QMenu::item:selected {
                background-color: #e0e0e0;
            }
            QMenu::separator {
                height: 1px;
                background-color: #ddd;
                margin: 5px 0;
            }
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0,
                    x2: 0, y2: 1,
                    stop: 0 #5c9ce6,
                    stop: 0.4 #4682B4,
                    stop: 0.5 #4682B4,
                    stop: 1.0 #3d6d99
                );
                color: white;
                border: none;
                border-radius: 8px;
                padding: 15px 35px;
                font-size: 14px;
                min-width: 150px;
                font-weight: bold;
                border: 1px solid #3d6d99;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0,
                    x2: 0, y2: 1,
                    stop: 0 #6baffa,
                    stop: 0.4 #5c9ce6,
                    stop: 0.5 #5c9ce6,
                    stop: 1.0 #4682B4
                );
                border: 1px solid #4682B4;
            }
            QPushButton:pressed {
                background: qlineargradient(
                    x1: 0, y1: 0,
                    x2: 0, y2: 1,
                    stop: 0 #3d6d99,
                    stop: 0.4 #4682B4,
                    stop: 0.5 #4682B4,
                    stop: 1.0 #5c9ce6
                );
                border: 1px solid #3d6d99;
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        # 添加顶部弹性空间
        main_layout.addStretch(1)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        
        # 创建功能区域（按钮+说明）
        buttons = ["视频压缩", "视频分割", "音频转换"]
        descriptions = [
            "将大视频文件压缩为更小的文件\n支持多种分辨率选择\n保持视频质量的同时减小文件体积",
            "将视频文件分割为多个小片段\n自动分割为不超过50MB的片段\n保持原视频质量不变",
            "将各种格式的音频转换为MP3格式\n支持批量转换\n统一音频输出格式"
        ]
        
        for text, desc in zip(buttons, descriptions):
            # 创建功能容器
            feature_container = QWidget()
            feature_layout = QVBoxLayout(feature_container)
            feature_layout.setSpacing(20)
            feature_layout.setContentsMargins(0, 0, 0, 0)
            
            # 创建按钮
            btn = AnimatedButton(text, self)
            btn.setFixedSize(200, 200)
            btn.clicked.connect(self.on_button_click)
            feature_layout.addWidget(btn)
            self.buttons.append(btn)
            
            # 创建说明标签
            desc_label = QLabel(desc)
            desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            desc_label.setStyleSheet("""
                QLabel {
                    color: #666;
                    font-size: 12px;
                    padding: 10px;
                    margin-top: 10px;
                    background-color: #f8f8f8;
                    border-radius: 5px;
                }
            """)
            desc_label.setWordWrap(True)
            desc_label.setFixedHeight(80)
            feature_layout.addWidget(desc_label)
            
            # 添加到按钮布局
            button_layout.addWidget(feature_container)
        
        # 添加按钮布局到主布局
        main_layout.addLayout(button_layout)
        
        # 添加底部弹性空间
        main_layout.addStretch(1)
        
        # 启动入场动画
        QTimer.singleShot(100, self.start_entrance_animation)
    
    def animate_button(self, button: QPushButton, y_offset: int) -> None:
        """按钮动画"""
        anim = QPropertyAnimation(button, b"pos", self)
        anim.setDuration(100)
        anim.setStartValue(button.pos())
        anim.setEndValue(QPoint(button.x(), button.y() + y_offset))
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
    
    def on_button_click(self) -> None:
        """按钮点击事件"""
        sender = cast(QPushButton, self.sender())
        if sender:
            if sender.text() == "视频压缩":
                self.show_compress_dialog()
            elif sender.text() == "视频分割":
                self.show_split_dialog()
            elif sender.text() == "音频转换":
                self.show_convert_dialog()
    
    def show_compress_dialog(self):
        dialog = CompressDialog(self)
        dialog.exec()
    
    def show_split_dialog(self):
        dialog = SplitDialog(self)
        dialog.exec()
    
    def show_convert_dialog(self):
        """打开音频转换对话框"""
        dialog = ConvertDialog(self)
        dialog.exec()
    
    def start_entrance_animation(self):
        """按钮入场动画"""
        for i, btn in enumerate(self.buttons):
            # 创建位置动画
            anim = QPropertyAnimation(btn, b"pos")
            anim.setDuration(500)
            anim.setStartValue(QPoint(btn.x(), btn.y() + 50))
            anim.setEndValue(QPoint(btn.x(), btn.y()))
            anim.setEasingCurve(QEasingCurve.Type.OutBack)
            
            # 延迟启动每个按钮的动画
            QTimer.singleShot(i * 100, anim.start)
    
    def create_menu_bar(self) -> None:
        """创建菜单栏"""
        menubar = cast(QMenuBar, self.menuBar())
        
        # 工具菜单
        tools_menu = cast(QMenu, menubar.addMenu("工具"))
        
        # 视频压缩
        compress_action = QAction("视频压缩", self)
        compress_action.triggered.connect(self.show_compress_dialog)
        tools_menu.addAction(compress_action)
        
        # 视频分割
        split_action = QAction("视频分割", self)
        split_action.triggered.connect(self.show_split_dialog)
        tools_menu.addAction(split_action)
        
        # 音频转换
        convert_action = QAction("音频转换", self)
        convert_action.triggered.connect(self.show_convert_dialog)
        tools_menu.addAction(convert_action)
        
        tools_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        tools_menu.addAction(exit_action)
        
        # 帮助菜单
        about_menu = cast(QMenu, menubar.addMenu("关于"))
        if about_menu is None:
            return
        
        # 关于
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        about_menu.addAction(about_action)
    
    def show_about(self):
        """显示关于对话框"""
        current_year = datetime.now().year
        QMessageBox.about(self, "关于音视频处理工作台",
            "音视频处理工作台 v1.0\n\n"
            "一个简单的视频处理工具集合，包含：\n"
            "- 视频压缩\n"
            "- 视频分割\n"
            "- 音频转换\n\n"
            "作者：tiankong214\n"
            f"版权所有 © {current_year}"
        ) 