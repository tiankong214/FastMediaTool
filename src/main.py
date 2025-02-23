import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
import logging
import subprocess
import traceback
from main_window import MainWindow

# 只保留文件日志
file_handler = logging.FileHandler('app.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# 配置日志记录器
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

def global_exception_handler(exctype, value, tb):
    """全局异常处理"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    logging.error(f"未捕获的异常:\n{error_msg}")
    with open('error.log', 'a', encoding='utf-8') as f:
        f.write(f"\n{error_msg}")

# 设置全局异常处理器
sys.excepthook = global_exception_handler

def main():
    # 在 Windows 系统上隐藏控制台窗口
    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.ShowWindow(
            ctypes.windll.kernel32.GetConsoleWindow(), 0)
    
    app = QApplication(sys.argv)
    
    # 检查 FFmpeg 是否可用
    try:
        subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    except FileNotFoundError:
        QMessageBox.critical(None, "错误", "请先安装 FFmpeg")
        return
    
    # 设置应用程序图标
    icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'icons', 'app.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 