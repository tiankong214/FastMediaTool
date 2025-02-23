from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                            QFileDialog, QProgressBar, QHBoxLayout, QListWidget,
                            QMessageBox, QWidget, QLineEdit, QListWidgetItem)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QColor, QBrush
import os
import subprocess
from .log_widget import LogWidget
from typing import List
import av
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

class ConvertWorker(QThread):
    progress = pyqtSignal(int)  # 总进度
    file_completed = pyqtSignal(int)  # 已完成的文件数
    finished = pyqtSignal(bool, str)
    log_message = pyqtSignal(str, str)
    
    def __init__(self, input_files: List[str], output_dir: str):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.is_cancelled = False
    
    def run(self):
        try:
            total_files = len(self.input_files)
            converted_count = 0
            
            # 顺序处理每个文件
            for i, input_file in enumerate(self.input_files):
                if self.is_cancelled:
                    break
                
                # 转换单个文件
                if self.convert_file(input_file, i, total_files):
                    converted_count += 1
                    # 发送已完成文件数
                    self.file_completed.emit(converted_count)
                else:
                    # 如果转换失败，继续处理下一个文件
                    continue
            
            if self.is_cancelled:
                self.finished.emit(False, "已取消转换")
            else:
                self.finished.emit(
                    converted_count == total_files,
                    f"完成 {converted_count}/{total_files} 个文件的转换"
                )
            
        except Exception as e:
            self.log_message.emit(f"转换过程出错: {str(e)}", "ERROR")
            self.finished.emit(False, str(e))

    def convert_file(self, input_file: str, index: int, total_files: int) -> bool:
        try:
            filename = os.path.splitext(os.path.basename(input_file))[0]
            output_path = os.path.join(self.output_dir, f"{filename}.mp3")
            
            self.log_message.emit(f"开始转换：{filename}", "INFO")
            
            # 创建 startupinfo 对象来隐藏命令行窗口
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # 构建 FFmpeg 命令
            command = [
                'ffmpeg', '-y',
                '-hide_banner',
                '-i', input_file,
                '-acodec', 'libmp3lame',
                '-ab', '192k',
                output_path
            ]
            
            # 执行转换
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                encoding='utf-8',
                errors='ignore'
            )
            
            # 等待转换完成
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                progress = int(((index + 1) * 100) / total_files)
                self.progress.emit(progress)  # 发送总进度
                self.log_message.emit(f"转换完成：{filename}", "INFO")
                return True
            else:
                self.log_message.emit(f"转换失败：{stderr}", "ERROR")
                return False
                
        except Exception as e:
            self.log_message.emit(f"转换 {filename} 失败: {str(e)}", "ERROR")
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            return False

    def terminate(self):
        """终止转换"""
        self.is_cancelled = True
        super().terminate()

class ConvertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("音视频处理工作台 - 音频转换")
        self.setMinimumSize(600, 400)
        
        # 初始化变量
        self.input_files = []
        self.worker = None
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 添加打开文件按钮
        open_button = QPushButton("打开音频文件")
        open_button.clicked.connect(self.select_files)
        layout.addWidget(open_button)
        
        # 文件列表区域
        lists_layout = QHBoxLayout()
        
        # 输入文件列表
        input_list_container = QWidget()
        input_list_layout = QVBoxLayout(input_list_container)
        input_list_layout.setContentsMargins(0, 0, 0, 0)
        
        input_list_layout.addWidget(QLabel("输入文件："))
        self.input_list = QListWidget()
        self.input_list.setStyleSheet("""
            QListWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        input_list_layout.addWidget(self.input_list)
        
        # 输出文件列表
        output_list_container = QWidget()
        output_list_layout = QVBoxLayout(output_list_container)
        output_list_layout.setContentsMargins(0, 0, 0, 0)
        
        output_label = QLabel("输出文件：")
        self.output_list = QListWidget()
        self.output_list.setStyleSheet("""
            QListWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        output_list_layout.addWidget(output_label)
        output_list_layout.addWidget(self.output_list)
        
        lists_layout.addWidget(input_list_container)
        lists_layout.addWidget(output_list_container)
        
        # 将文件列表布局添加到主布局
        layout.addLayout(lists_layout)
        
        # 添加日志组件
        self.log_widget = LogWidget()
        layout.addWidget(self.log_widget)
        self.log_widget.setFixedHeight(150)
        
        # 在进度条之前添加输出目录选择
        output_settings = QWidget()
        output_settings_layout = QVBoxLayout(output_settings)
        output_settings_layout.setSpacing(5)
        output_settings_layout.setContentsMargins(0, 0, 0, 0)
        
        # 输出目录
        output_dir_layout = QHBoxLayout()
        output_dir_layout.setSpacing(5)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        self.output_dir_edit.clear()  # 确保初始为空
        self.output_dir_edit.setPlaceholderText("请先选择音频文件")
        self.output_dir_button = QPushButton("浏览")
        self.output_dir_button.clicked.connect(self.select_output_dir)
        self.output_dir_button.setEnabled(False)  # 初始禁用
        output_dir_layout.addWidget(QLabel("输出目录："))
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(self.output_dir_button)
        output_settings_layout.addLayout(output_dir_layout)
        
        layout.addWidget(output_settings)
        
        # 添加状态标签
        self.status_label = QLabel("等待开始...")
        layout.addWidget(self.status_label)
        
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
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.start_button = QPushButton("开始转换")
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
        
        # 添加按钮到布局
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.back_button)
        layout.addLayout(button_layout)
        
        # 连接按钮信号
        self.start_button.clicked.connect(self.start_convert)
        self.cancel_button.clicked.connect(self.cancel_convert)
        self.back_button.clicked.connect(self.reject)
        
        # 设置按钮初始状态
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        # 设置拖放
        self.setAcceptDrops(True)
    
    def select_files(self):
        """选择音频文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择音频文件",
            "",
            "音频文件 (*.mp3 *.wav *.ogg *.m4a *.wma *.aac *.flac);;所有文件 (*.*)"
        )
        if files:
            self.add_files(files)
    
    def select_output_dir(self):
        """选择输出目录"""
        # 先检查是否有选择文件
        if not self.input_files:
            QMessageBox.warning(
                self,
                "提示",
                "请先选择音频文件",
                QMessageBox.StandardButton.Ok
            )
            return

        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            os.path.dirname(self.input_files[0]) if self.input_files else ""
        )
        if dir_path:
            # 检查是否选择了输入文件所在目录
            if any(os.path.dirname(f) == dir_path for f in self.input_files):
                QMessageBox.warning(
                    self,
                    "警告",
                    "不建议选择输入文件所在目录作为输出目录，这可能会覆盖原文件。\n建议选择其他目录。",
                    QMessageBox.StandardButton.Ok
                )
            self.output_dir_edit.setText(dir_path)

    def add_files(self, files):
        """添加文件到列表"""
        for file_path in files:
            if file_path not in self.input_files:
                self.log_widget.log(f"添加文件：{file_path}")
                self.input_files.append(file_path)
                # 添加到输入列表
                self.input_list.addItem(os.path.basename(file_path))
                # 添加到输出列表（显示转换后的文件名）
                output_name = os.path.splitext(os.path.basename(file_path))[0] + ".mp3"
                self.output_list.addItem(output_name)
        
        # 启用输出目录选择按钮
        self.output_dir_button.setEnabled(True)
        # 清空输出目录
        self.output_dir_edit.clear()
        self.output_dir_edit.setPlaceholderText("请选择输出目录")
        # 只要有输入文件就启用开始按钮
        self.start_button.setEnabled(True)

    def start_convert(self):
        """开始转换"""
        try:
            if not self.input_files:
                QMessageBox.warning(
                    self,
                    "提示",
                    "请先选择音频文件",
                    QMessageBox.StandardButton.Ok
                )
                return
            
            # 检查输出目录
            output_dir = self.output_dir_edit.text().strip()
            if not output_dir:
                QMessageBox.warning(
                    self,
                    "提示",
                    "请选择输出目录",
                    QMessageBox.StandardButton.Ok
                )
                return
            
            # 检查输出目录是否存在
            if not os.path.exists(output_dir):
                reply = QMessageBox.question(
                    self,
                    "提示",
                    "输出目录不存在，是否创建？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    try:
                        os.makedirs(output_dir)
                    except Exception as e:
                        QMessageBox.critical(
                            self,
                            "错误",
                            f"创建目录失败：{str(e)}",
                            QMessageBox.StandardButton.Ok
                        )
                        return
                else:
                    return
            
            # 检查输出文件是否已存在
            existing_files = []
            for file_path in self.input_files:
                output_name = os.path.splitext(os.path.basename(file_path))[0] + ".mp3"
                output_path = os.path.join(output_dir, output_name)
                if os.path.exists(output_path):
                    existing_files.append(output_name)
            
            if existing_files:
                msg = "以下文件已存在，是否覆盖？\n\n" + "\n".join(existing_files)
                reply = QMessageBox.question(
                    self,
                    "确认覆盖",
                    msg,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            total_files = len(self.input_files)
            self.log_widget.log(f"开始转换 {total_files} 个文件")
            self.log_widget.log(f"输出目录：{output_dir}")
            
            # 重置进度条和状态
            self.progress.setValue(0)
            self.status_label.setText(f"正在转换 (0/{total_files})")
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            # 创建并启动工作线程
            self.worker = ConvertWorker(self.input_files, output_dir)
            self.worker.progress.connect(self.update_progress)
            self.worker.file_completed.connect(self.update_completed_files)
            self.worker.finished.connect(self.conversion_finished)
            self.worker.log_message.connect(self.log_widget.log)
            self.worker.start()
            
        except Exception as e:
            self.log_widget.log(f"启动转换失败：{str(e)}", "ERROR")

    def update_completed_files(self, completed_count: int):
        """更新已完成文件数"""
        total_files = len(self.input_files)
        self.status_label.setText(f"正在转换 ({completed_count}/{total_files})")

    def update_progress(self, value):
        """更新进度条"""
        self.progress.setValue(value)

    def conversion_finished(self, success, message):
        """转换完成回调"""
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        total_files = len(self.input_files)
        
        if success:
            self.progress.setValue(100)
            self.status_label.setText(f"转换完成 ({total_files}/{total_files})")
            self.log_widget.log("所有文件转换完成", "INFO")
        else:
            self.status_label.setText(f"转换失败：{message}")
            self.log_widget.log(f"转换失败：{message}", "ERROR")

    def cancel_convert(self):
        """取消转换"""
        if self.worker and self.worker.isRunning():
            self.log_widget.log("正在取消转换...", "WARNING")
            self.cancel_button.setEnabled(False)
            self.worker.terminate()
            self.worker.wait()
            self.worker = None
            
            # 更新UI状态
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            # 取消时不重置进度条，保持当前进度
            self.status_label.setText("转换已取消")
            self.log_widget.log("已取消转换", "INFO")
            
            # 移除这里的 self.reject() 或 self.close() 调用 

    def show_error_message(self, message: str) -> None:
        """显示错误消息"""
        self.log_widget.log(message, "ERROR")
    
    def show_success_message(self) -> None:
        """显示成功消息"""
        self.log_widget.log("转换完成", "INFO") 