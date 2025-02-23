import os
import shutil

def copy_icon():
    # 获取当前脚本的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 源图标路径 - 修改为从 resources 目录读取
    source_icon = os.path.join(current_dir, "resources", "icon.ico")
    
    if not os.path.exists(source_icon):
        print(f"错误：找不到源图标文件: {source_icon}")
        return
    
    # 创建目标目录
    src_icon_dir = os.path.join(current_dir, 'src', 'resources', 'icons')
    os.makedirs(src_icon_dir, exist_ok=True)
    
    # 目标图标路径
    target_icon = os.path.join(src_icon_dir, 'app.ico')
    
    # 复制图标文件
    shutil.copy2(source_icon, target_icon)
    print(f"图标已复制到: {target_icon}")

if __name__ == '__main__':
    copy_icon() 