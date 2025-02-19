from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                            QFileDialog, QProgressBar, QHBoxLayout, QListWidget,
                            QMessageBox, QWidget, QLineEdit, QListWidgetItem)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QColor, QBrush
import os
import subprocess

class ConvertWorker(QThread):
    progress = pyqtSignal(int, str, str)  # 进度值, 当前处理的文件名, 状态信息
    finished = pyqtSignal(bool, str)
    
    def __init__(self, input_files, output_dir):
        super().__init__()
        self.input_files = input_files
        self.output_dir = output_dir
        self.process = None
        self.is_cancelled = False
    
    def run(self):
        try:
            total_files = len(self.input_files)
            converted_count = 0
            
            for i, input_file in enumerate(self.input_files):
                if self.is_cancelled:
                    break
                
                # 获取输出文件名
                filename = os.path.splitext(os.path.basename(input_file))[0]
                output_path = os.path.join(self.output_dir, f"{filename}.mp3")
                
                # 更新状态：开始转换当前文件
                status = f"正在转换: {filename} ({i+1}/{total_files})"
                self.progress.emit(int((i * 100) / total_files), filename, status)
                
                # 构建 FFmpeg 命令
                command = [
                    'ffmpeg', '-y',
                    '-i', input_file,
                    '-vn',
                    '-acodec', 'libmp3lame',
                    '-ab', '192k',
                    '-ar', '44100',
                    '-ac', '2',
                    output_path
                ]
                
                print(f"执行命令: {' '.join(command)}")
                
                try:
                    # 执行转换
                    process = subprocess.run(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8',
                        errors='replace'
                    )
                    
                    # 检查转换结果
                    if process.returncode == 0 and os.path.exists(output_path):
                        converted_count += 1
                        # 发送完成信号
                        progress = int(((i + 1) * 100) / total_files)
                        self.progress.emit(progress, filename, f"完成:{filename}")
                    else:
                        print(f"转换失败: {input_file}")
                        print(f"错误输出: {process.stderr}")
                        self.progress.emit(int((i + 1) * 100 / total_files), filename, f"失败:{filename}")
                
                except Exception as e:
                    print(f"转换出错: {str(e)}")
                    self.progress.emit(int((i + 1) * 100 / total_files), filename, f"失败:{filename}")
            
            # 检查是否所有文件都转换成功
            if converted_count == total_files:
                self.finished.emit(True, "所有文件转换完成")
            else:
                self.finished.emit(True, f"完成 {converted_count}/{total_files} 个文件的转换")
            
        except Exception as e:
            print(f"转换过程出错: {str(e)}")
            import traceback
            traceback.print_exc()
            self.finished.emit(False, str(e))

    def terminate(self):
        self.is_cancelled = True
        if self.process:
            print("正在终止FFmpeg进程...")
            self.process.terminate()
            self.process.wait()
            print("FFmpeg进程已终止")
        super().terminate()

class ConvertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("音频转换 - 音视频处理工作台")
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
        
        layout.addLayout(lists_layout)
        
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
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.back_button)
        layout.addLayout(button_layout)
        
        # 连接信号
        self.start_button.clicked.connect(self.start_convert)
        self.cancel_button.clicked.connect(self.cancel_convert)
        self.back_button.clicked.connect(self.reject)
        
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
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)

    def add_files(self, files):
        """添加文件到列表"""
        for file_path in files:
            if file_path not in self.input_files:
                self.input_files.append(file_path)
                # 添加到输入列表
                self.input_list.addItem(os.path.basename(file_path))
                # 添加到输出列表（显示转换后的文件名）
                output_name = os.path.splitext(os.path.basename(file_path))[0] + ".mp3"
                self.output_list.addItem(output_name)  # 直接添加文件名，不设置颜色
        
        # 设置默认输出目录为第一个文件所在目录下的 converted 文件夹
        if self.input_files:
            first_file_dir = os.path.dirname(self.input_files[0])
            default_output_dir = os.path.join(first_file_dir, "converted_audio")
            # 创建输出目录（如果不存在）
            if not os.path.exists(default_output_dir):
                os.makedirs(default_output_dir)
            self.output_dir_edit.setText(default_output_dir)
        
        # 启用相关控件
        self.output_dir_button.setEnabled(True)
        self.start_button.setEnabled(len(self.input_files) > 0)
    
    def start_convert(self):
        """开始转换"""
        if not self.input_files:
            return
        
        # 检查输出目录
        output_dir = self.output_dir_edit.text()
        if not output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return
        
        # 开始转换
        self.progress.setValue(0)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        
        self.worker = ConvertWorker(self.input_files, output_dir)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.conversion_finished)
        self.worker.start()
    
    def update_progress(self, value, filename, status):
        """更新进度和状态"""
        self.progress.setValue(value)
        
        # 更新状态标签
        if not status.startswith(("完成:", "失败:")):
            self.status_label.setText(status)
    
    def conversion_finished(self, success, message):
        """转换完成回调"""
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if success:
            self.status_label.setText(message)
            QMessageBox.information(self, "完成", message)
        else:
            self.status_label.setText(f"转换失败：{message}")
            QMessageBox.warning(self, "错误", f"转换失败：{message}")
        
        self.progress.setValue(0)
    
    def cancel_convert(self):
        """取消转换"""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.progress.setValue(0) 