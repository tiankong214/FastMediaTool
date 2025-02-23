import os
from PIL import Image, ImageDraw

def create_gradient_circle(size, center, radius, start_color, end_color):
    """创建渐变圆"""
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    
    # 创建渐变效果
    for i in range(int(radius)):
        opacity = int(255 * (1 - i/radius))
        mask_draw.ellipse(
            [center[0] - (radius-i), center[1] - (radius-i),
             center[0] + (radius-i), center[1] + (radius-i)],
            fill=opacity
        )
    
    # 创建渐变色圆
    gradient = Image.new('RGBA', (size, size), start_color)
    gradient.putalpha(mask)
    return gradient

def create_3d_icon():
    # 获取当前脚本的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建图标
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 颜色定义
    primary_dark = '#1565C0'   # 深蓝
    primary_light = '#42A5F5'  # 亮蓝
    accent_dark = '#C2185B'    # 深粉
    accent_light = '#EC407A'   # 亮粉
    highlight = '#FFFFFF'      # 高光色
    
    center = size // 2
    radius = int(size // 3)
    
    # 创建主圆形的3D效果
    # 1. 底部阴影
    shadow_offset = 8
    shadow_radius = int(radius + 4)
    shadow = create_gradient_circle(
        size,
        (center, center + shadow_offset),
        shadow_radius,
        (0, 0, 0, 100),
        (0, 0, 0, 0)
    )
    img.paste(shadow, (0, 0), shadow)
    
    # 2. 主圆形
    main_circle = create_gradient_circle(
        size,
        (center, center),
        radius,
        primary_dark,
        primary_light
    )
    img.paste(main_circle, (0, 0), main_circle)
    
    # 3. 内部装饰圆环
    inner_radius = int(radius * 0.7)
    draw.arc(
        [center - inner_radius, center - inner_radius,
         center + inner_radius, center + inner_radius],
        0, 360, fill=highlight, width=2
    )
    
    # 4. 功能图标
    icon_size = int(radius * 0.4)
    
    # 视频图标（带3D效果）
    video_x = int(center - icon_size * 1.2)
    video_y = center - icon_size
    # 视频图标底部阴影
    draw.rectangle(
        [video_x+2, video_y+2, video_x + icon_size+2, video_y + icon_size+2],
        fill=(0, 0, 0, 50)
    )
    # 视频图标主体
    draw.rectangle(
        [video_x, video_y, video_x + icon_size, video_y + icon_size],
        fill=accent_light
    )
    # 播放三角形
    play_points = [
        (int(video_x + icon_size*0.3), int(video_y + icon_size*0.25)),
        (int(video_x + icon_size*0.3), int(video_y + icon_size*0.75)),
        (int(video_x + icon_size*0.8), int(video_y + icon_size*0.5))
    ]
    draw.polygon(play_points, fill=highlight)
    
    # 分割图标（带3D效果）
    split_x = int(center + icon_size * 0.4)
    split_y = center - icon_size
    for i in range(3):
        x = int(split_x + (i * icon_size * 0.5))
        # 阴影
        draw.rectangle(
            [x+2, split_y+2, x + int(icon_size*0.3)+2, split_y + icon_size+2],
            fill=(0, 0, 0, 50)
        )
        # 主体
        draw.rectangle(
            [x, split_y, x + int(icon_size*0.3), split_y + icon_size],
            fill=accent_dark if i % 2 == 0 else accent_light
        )
    
    # 音频波形（带3D效果）
    wave_x = int(center - icon_size * 1.5)
    wave_y = int(center + icon_size * 0.5)
    for i in range(5):
        x = int(wave_x + (i * icon_size * 0.6))
        height = int(icon_size * (1 if i % 2 == 0 else 0.6))
        # 阴影
        draw.rectangle(
            [x+2, wave_y+2, x + int(icon_size*0.3)+2, wave_y + height+2],
            fill=(0, 0, 0, 50)
        )
        # 主体
        draw.rectangle(
            [x, wave_y, x + int(icon_size*0.3), wave_y + height],
            fill=accent_light if i % 2 == 0 else accent_dark
        )
    
    # 5. 高光效果
    highlight_radius = int(radius * 0.9)
    highlight_offset = int(radius * 0.3)
    highlight = create_gradient_circle(
        size,
        (center - highlight_offset, center - highlight_offset),
        highlight_radius,
        (255, 255, 255, 50),
        (255, 255, 255, 0)
    )
    img.paste(highlight, (0, 0), highlight)
    
    # 保存图标
    icon_path = os.path.join(current_dir, 'icon.ico')
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(icon_path, format='ICO', sizes=sizes)
    print(f"图标已创建: {icon_path}")

if __name__ == '__main__':
    create_3d_icon() 