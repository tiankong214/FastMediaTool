import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
import logging
import subprocess
import traceback
from main_window import MainWindow

# 配置日志记录
def setup_logging():
    """配置日志记录器"""
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s'
    )
    
    # 配置文件日志
    file_handler = logging.FileHandler('app.log', encoding='utf-8', mode='w')  # 使用 'w' 模式清空旧日志
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 配置控制台日志
    console_handler = logging.StreamHandler(sys.stdout)  # 明确指定输出到 stdout
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    for handler in root_logger.handlers[:]:  # 清除现有的处理器
        root_logger.removeHandler(handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 记录初始信息
    logging.info("日志系统初始化完成")
    logging.info(f"Python 版本: {sys.version}")
    logging.info(f"运行路径: {os.getcwd()}")

def global_exception_handler(exctype, value, tb):
    """全局异常处理"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    logging.error(f"未捕获的异常:\n{error_msg}")
    with open('error.log', 'a', encoding='utf-8') as f:
        f.write(f"\n{error_msg}")
    
    # 显示错误对话框
    QMessageBox.critical(
        None,
        "错误",
        f"发生错误:\n{str(value)}\n\n详细信息已记录到 error.log"
    )

def main():
    """主函数"""
    try:
        # 设置日志记录
        setup_logging()
        logging.info("应用程序启动")
        
        # 在 Windows 上隐藏控制台窗口
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.ShowWindow(
                ctypes.windll.kernel32.GetConsoleWindow(), 0)
        
        # 创建应用程序
        app = QApplication(sys.argv)
        
        # 检查 FFmpeg 是否可用
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
        except FileNotFoundError:
            logging.error("FFmpeg 未安装")
            QMessageBox.critical(None, "错误", "请先安装 FFmpeg")
            return
        
        # 设置应用程序图标
        icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'icons', 'app.ico')
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            logging.info(f"已加载应用程序图标: {icon_path}")
        else:
            logging.warning(f"找不到应用程序图标: {icon_path}")
        
        # 创建并显示主窗口
        window = MainWindow()
        window.show()
        logging.info("主窗口已显示")
        
        # 运行应用程序
        sys.exit(app.exec())
        
    except Exception as e:
        error_msg = f"应用程序错误:\n"
        error_msg += f"错误类型: {type(e).__name__}\n"
        error_msg += f"错误信息: {str(e)}\n"
        error_msg += f"堆栈跟踪:\n{traceback.format_exc()}"
        logging.error(error_msg)
        
        # 同时显示错误对话框
        QMessageBox.critical(
            None,
            "错误",
            f"应用程序发生错误:\n"
            f"类型: {type(e).__name__}\n"
            f"信息: {str(e)}\n\n"
            f"详细信息已记录到日志文件"
        )
        sys.exit(1)

if __name__ == '__main__':
    # 设置全局异常处理器
    sys.excepthook = global_exception_handler
    main() 