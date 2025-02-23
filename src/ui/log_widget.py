from PyQt6.QtWidgets import QTextEdit, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from datetime import datetime

class LogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建日志文本框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        layout.addWidget(self.log_text)
    
    def log(self, message, level="INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = {
            "INFO": "#4CAF50",    # 绿色
            "WARNING": "#FFC107",  # 黄色
            "ERROR": "#F44336",    # 红色
            "DEBUG": "#2196F3"     # 蓝色
        }.get(level, "#FFFFFF")    # 默认白色
        
        html = f'<span style="color: {color}">[{level}]</span> {timestamp} - {message}<br>'
        self.log_text.insertHtml(html)
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def clear(self):
        """清空日志"""
        self.log_text.clear() 