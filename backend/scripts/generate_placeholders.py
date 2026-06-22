import os
from PIL import Image, ImageDraw, ImageFont

def generate_placeholder(class_name, output_dir="static/portraits/defaults"):
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a simple dark gray image
    img = Image.new('RGB', (512, 512), color=(30, 30, 35))
    draw = ImageDraw.Draw(img)
    
    # Draw a silhouette-like shape
    draw.ellipse((156, 100, 356, 300), fill=(50, 50, 60))
    draw.pieslice((106, 300, 406, 700), start=180, end=360, fill=(50, 50, 60))
    
    # Text
    text = class_name.upper()
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
        
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    
    draw.text(((512 - text_w) / 2, 400), text, fill=(150, 150, 150), font=font)
    
    path = os.path.join(output_dir, f"default_{class_name.lower().replace(' ', '_')}.png")
    img.save(path)
    print(f"Generated {path}")

# Only base/starting classes need placeholders — evolutions are reached via
# leveling, by which point the hero already has a real generated portrait.
from services.class_service import COMBAT_BASE_CLASSES, SUPPORT_BASE_CLASSES

if __name__ == "__main__":
    for cls in set(COMBAT_BASE_CLASSES + SUPPORT_BASE_CLASSES + ["Classless"]):
        generate_placeholder(cls)
