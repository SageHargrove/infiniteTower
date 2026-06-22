import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs("static/portraits/defaults", exist_ok=True)

COLORS = {
    1: "#888888",
    2: "#aaaaaa",
    3: "#88b8c8",
    4: "#88c888",
    5: "#c8a840",
    6: "#c87840",
    7: "#c840c8",
}

for star, color in COLORS.items():
    img = Image.new("RGB", (512, 768), color="#16161e")
    draw = ImageDraw.Draw(img)
    
    # Draw border
    draw.rectangle([10, 10, 502, 758], outline=color, width=4)
    
    # Draw text
    text = "★" * star
    # We won't use a specific font to avoid missing font issues, just basic drawing if possible, or we can just draw stars as polygons.
    
    # Draw simple stars
    center_y = 768 // 2
    spacing = 40
    start_x = (512 - (star * spacing)) // 2 + (spacing // 2)
    
    for i in range(star):
        x = start_x + (i * spacing)
        # Draw a small circle as a star for simplicity
        draw.ellipse([x-10, center_y-10, x+10, center_y+10], fill=color)
        
    img.save(f"static/portraits/defaults/default_{star}star.png")
    print(f"Created default_{star}star.png")
