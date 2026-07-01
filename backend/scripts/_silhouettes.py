"""Hand-drawn (via PIL primitives) reference silhouettes for img2img seeding.

The checkpoint can't reliably invent a correct weapon/armor SHAPE from text
alone (see generate_equipment_icons.py's docstring) — these give it a
correct composition to restyle instead, at a moderate denoise so the shape
survives but the rendering/shading is the checkpoint's own.
"""
from PIL import Image, ImageDraw

SIZE = 768
MID = SIZE // 2

def _new():
    img = Image.new("RGB", (SIZE, SIZE), (10, 10, 10))
    return img, ImageDraw.Draw(img)

def sword():
    img, d = _new()
    # blade
    d.polygon([(MID, 90), (MID - 22, 480), (MID, 520), (MID + 22, 480)], fill=(210, 210, 220))
    # crossguard
    d.rectangle([MID - 70, 480, MID + 70, 510], fill=(180, 150, 60))
    # handle + pommel
    d.rectangle([MID - 14, 510, MID + 14, 620], fill=(90, 60, 30))
    d.ellipse([MID - 20, 615, MID + 20, 655], fill=(180, 150, 60))
    return img

def dagger():
    img, d = _new()
    # Asymmetric curved/jagged "dragon fang" blade per reference image —
    # one smooth curved edge, one jagged serrated edge — instead of a
    # symmetric leaf shape, which kept getting reinterpreted as a small
    # sword or an abstract cross. Still kept short (well under half the
    # canvas) so it stays dagger-proportioned.
    d.polygon([
        (MID + 10, 280),
        (MID - 8, 340), (MID + 2, 360), (MID - 14, 400), (MID - 2, 415),
        (MID - 20, 450), (MID - 6, 460), (MID - 16, 490),
        (MID + 10, 520),
        (MID + 26, 460), (MID + 30, 400), (MID + 24, 340),
    ], fill=(180, 40, 35))
    d.rectangle([MID - 6, 520, MID + 26, 545], fill=(60, 50, 45))
    d.polygon([(MID - 2, 545), (MID + 30, 545), (MID + 14, 600)], fill=(40, 35, 30))
    return img

def spear():
    img, d = _new()
    d.polygon([(MID, 60), (MID - 26, 220), (MID, 250), (MID + 26, 220)], fill=(210, 210, 220))
    d.rectangle([MID - 8, 250, MID + 8, 690], fill=(90, 60, 30))
    return img

def staff():
    img, d = _new()
    d.rectangle([MID - 10, 280, MID + 10, 700], fill=(70, 45, 25))
    d.ellipse([MID - 55, 110, MID + 55, 220], fill=(80, 180, 230))
    d.ellipse([MID - 30, 230, MID + 30, 290], fill=(180, 150, 60))
    return img

def bow():
    img, d = _new()
    # wider, shallower arc (a real recurve silhouette) instead of the tight
    # near-vertical curve that kept reading as a curved blade/claw
    d.arc([MID - 220, 60, MID + 120, 710], start=70, end=290, fill=(120, 80, 40), width=26)
    d.line([(MID - 95, 110), (MID - 95, 655)], fill=(230, 230, 230), width=4)
    return img

def heavy_armor():
    img, d = _new()
    d.polygon([
        (MID - 160, 200), (MID - 90, 140), (MID + 90, 140), (MID + 160, 200),
        (MID + 130, 420), (MID + 70, 620), (MID - 70, 620), (MID - 130, 420),
    ], fill=(140, 145, 155))
    d.polygon([(MID - 160, 200), (MID - 220, 260), (MID - 150, 320), (MID - 110, 250)], fill=(120, 125, 135))
    d.polygon([(MID + 160, 200), (MID + 220, 260), (MID + 150, 320), (MID + 110, 250)], fill=(120, 125, 135))
    d.line([(MID, 160), (MID, 600)], fill=(90, 95, 105), width=6)
    return img

def brigandine():
    img, d = _new()
    d.polygon([
        (MID - 140, 210), (MID - 80, 150), (MID + 80, 150), (MID + 140, 210),
        (MID + 115, 410), (MID + 60, 600), (MID - 60, 600), (MID - 115, 410),
    ], fill=(90, 65, 40))
    for row in range(5):
        for col in range(4):
            x = MID - 90 + col * 60
            y = 230 + row * 70
            d.ellipse([x, y, x + 18, y + 18], fill=(160, 140, 90))
    return img

def light_armor():
    img, d = _new()
    d.polygon([
        (MID - 110, 220), (MID - 70, 160), (MID + 70, 160), (MID + 110, 220),
        (MID + 90, 400), (MID + 45, 560), (MID - 45, 560), (MID - 90, 400),
    ], fill=(80, 55, 35))
    d.line([(MID - 90, 250), (MID + 90, 250)], fill=(50, 35, 20), width=4)
    return img

def robe():
    img, d = _new()
    d.polygon([
        (MID - 50, 150), (MID + 50, 150), (MID + 160, 640), (MID - 160, 640),
    ], fill=(45, 35, 60))
    d.line([(MID, 150), (MID, 640)], fill=(190, 160, 70), width=6)
    d.ellipse([MID - 55, 110, MID + 55, 190], fill=(20, 15, 30))
    return img

SILHOUETTES = {
    "Sword": sword, "Spear": spear, "Staff": staff, "Bow": bow, "Dagger": dagger,
    "Heavy Armor": heavy_armor, "Brigandine": brigandine, "Light Armor": light_armor, "Robe": robe,
}
