"""
Composites hero portraits onto a tier-colored decorative card background.

Originally cut the portrait's own background away with rembg and pasted just
the character onto the template. Dropped that — rembg's saliency segmentation
kept misjudging the boundary on this flat-cel-shaded art style (chopping off
hair, necks, shoulders at random), and no amount of prompt tuning toward a
"keyable" background fixed it reliably. Instead the full rectangular portrait
(background included) gets fit into the frame with its edges feathered to
transparency, blending into the template's own dark vignette — no AI step
that can fail, and the portraits already use a dark/gradient background that
reads fine inside the card. Templates are generated once (deterministic, no
AI image calls) and cached to disk; composited cards are cached per (hero
portrait, tier) so this work only runs once per hero, not on every page view.
"""
import os
import math
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CANVAS_SIZE = (700, 1050)
TEMPLATE_DIR = os.path.join("static", "card_templates")
CARD_CACHE_DIR = os.path.join("static", "portraits", "cards")

# No local copy of the app's actual web font (Cinzel is loaded from Google
# Fonts at runtime, not bundled as a file) — Georgia Bold is a close-enough
# elegant serif already present on Windows, so no new asset/download needed.
_NAME_FONT_PATH = r"C:\Windows\Fonts\georgiab.ttf"


def _name_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(_NAME_FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()

TIER_COLORS = {
    "bronze": (140, 78, 38),    # deep copper-brown, pushed away from gold
    "silver": (196, 200, 212),
    "gold": (224, 170, 30),     # vivid yellow-gold, more saturated/brighter than bronze
    "prismatic": None,  # rainbow gradient, handled specially
}

PRISMATIC_HUES = [(255, 60, 60), (255, 200, 60), (80, 220, 120), (60, 180, 255), (180, 90, 255)]


def tier_for_star(birth_star: int) -> str:
    if birth_star >= 7:
        return "prismatic"
    if birth_star >= 5:
        return "gold"
    if birth_star >= 3:
        return "silver"
    return "bronze"


def _tier_color_at(tier: str, t: float) -> tuple:
    """t in [0,1] — for prismatic, samples around the hue wheel; for fixed
    tiers, just returns the flat color."""
    color = TIER_COLORS[tier]
    if color is not None:
        return color
    n = len(PRISMATIC_HUES)
    idx = t * n
    i0 = int(idx) % n
    i1 = (i0 + 1) % n
    frac = idx - int(idx)
    c0, c1 = PRISMATIC_HUES[i0], PRISMATIC_HUES[i1]
    return tuple(int(c0[k] + (c1[k] - c0[k]) * frac) for k in range(3))


def _draw_star(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: tuple):
    points = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        radius = r if i % 2 == 0 else r * 0.45
        points.append((cx + radius * math.cos(angle), cy - radius * math.sin(angle)))
    draw.polygon(points, fill=color)


def _build_template(tier: str) -> Image.Image:
    w, h = CANVAS_SIZE
    img = Image.new("RGB", (w, h), (10, 10, 12))
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = w // 2, int(h * 0.42)

    # Concentric medallion rings behind where the character will sit.
    max_r = int(w * 0.62)
    for i, r in enumerate(range(max_r, 30, -22)):
        t = 1 - (r / max_r)
        color = _tier_color_at(tier, t)
        alpha = max(8, 40 - i * 2)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*color, alpha), width=2)

    # Faint diagonal cross-hatch within the medallion, for the "etched metal" feel.
    hatch_color = _tier_color_at(tier, 0.5)
    step = 28
    for x in range(-h, w + h, step):
        draw.line([(x, 0), (x + h, h)], fill=(*hatch_color, 10), width=1)
        draw.line([(x, h), (x + h, 0)], fill=(*hatch_color, 10), width=1)

    # Outer ornate border — double rounded-rect outline + corner diamonds.
    margin = 18
    outer_color = _tier_color_at(tier, 0.0)
    draw.rounded_rectangle([margin, margin, w - margin, h - margin], radius=22, outline=(*outer_color, 230), width=6)
    draw.rounded_rectangle([margin + 14, margin + 14, w - margin - 14, h - margin - 14], radius=16, outline=(*outer_color, 140), width=2)

    diamond_r = 10
    for dx, dy in [(margin, margin), (w - margin, margin), (margin, h - margin), (w - margin, h - margin)]:
        diamond_color = _tier_color_at(tier, 0.25)
        draw.polygon([(dx, dy - diamond_r), (dx + diamond_r, dy), (dx, dy + diamond_r), (dx - diamond_r, dy)], fill=(*diamond_color, 255))

    # Star-tier icon medallion at the top. Sampled at a cooler point on the
    # prismatic wheel (blue) specifically so it never reads as gold-ish.
    icon_y = margin + 46
    icon_color = _tier_color_at(tier, 0.6)
    draw.ellipse([cx - 28, icon_y - 28, cx + 28, icon_y + 28], fill=(20, 20, 24, 255), outline=(*icon_color, 255), width=4)
    _draw_star(draw, cx, icon_y, 16, (*icon_color, 255))

    # Nameplate banner near the bottom — decorative band only, no baked-in
    # text (the app already renders the hero's name as a separate HTML
    # element below/over the portrait).
    band_top = int(h * 0.86)
    band_bot = int(h * 0.94)
    band_color = _tier_color_at(tier, 0.75)
    draw.rectangle([margin + 30, band_top, w - margin - 30, band_bot], fill=(14, 14, 16, 235), outline=(*band_color, 255), width=3)
    chevron_w = 24
    for side, x0 in [(-1, margin + 30), (1, w - margin - 30)]:
        ytop, ybot, ymid = band_top, band_bot, (band_top + band_bot) // 2
        tip = x0 + side * chevron_w
        draw.polygon([(x0, ytop), (tip, ymid), (x0, ybot)], fill=(*band_color, 255))

    return img


def get_template(tier: str) -> Image.Image:
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    path = os.path.join(TEMPLATE_DIR, f"{tier}.png")
    if not os.path.exists(path):
        img = _build_template(tier)
        img.save(path)
        return img
    return Image.open(path).convert("RGB")


FEATHER_PX = 36

def _fit_with_feathered_edges(portrait_path: str) -> Image.Image:
    """Load the portrait as-is (background included) with its outer edges
    faded to transparent, so pasting it onto the template blends into the
    template's own dark vignette instead of leaving a hard rectangular seam."""
    raw = Image.open(portrait_path).convert("RGBA")
    w, h = raw.size
    mask = Image.new("L", (w, h), 255)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rectangle([0, 0, w, FEATHER_PX], fill=0)
    mdraw.rectangle([0, h - FEATHER_PX, w, h], fill=0)
    mdraw.rectangle([0, 0, FEATHER_PX, h], fill=0)
    mdraw.rectangle([w - FEATHER_PX, 0, w, h], fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(FEATHER_PX * 0.6))
    raw.putalpha(mask)
    return raw


def _fit_name_font(draw: ImageDraw.ImageDraw, name: str, max_width: int, max_size: int = 52, min_size: int = 18) -> ImageFont.FreeTypeFont:
    size = max_size
    while size > min_size:
        font = _name_font(size)
        bbox = draw.textbbox((0, 0), name, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 2
    return _name_font(min_size)


def composite_card(hero_id: int, portrait_path: str, birth_star: int, hero_name: str = "") -> str:
    """Builds (or returns the cached) composited card image path for a hero.
    Cache key includes the portrait file's mtime (so a regenerated/rerolled
    portrait invalidates the old composited card) and a hash of the name (so
    a late-arriving LLM-enriched name also invalidates it)."""
    os.makedirs(CARD_CACHE_DIR, exist_ok=True)
    tier = tier_for_star(birth_star)
    mtime = int(os.path.getmtime(portrait_path))
    name_hash = abs(hash(hero_name)) % 100000
    out_path = os.path.join(CARD_CACHE_DIR, f"{hero_id}_{tier}_{mtime}_{name_hash}.png")
    if os.path.exists(out_path):
        return out_path

    template = get_template(tier).convert("RGBA")
    portrait = _fit_with_feathered_edges(portrait_path)

    w, h = template.size
    # Character fills most of the frame, anchored a bit above center so the
    # nameplate band and top icon stay clear.
    target_h = int(h * 0.78)
    scale = target_h / portrait.height
    target_w = int(portrait.width * scale)
    portrait = portrait.resize((target_w, target_h), Image.LANCZOS)

    paste_x = (w - target_w) // 2
    paste_y = int(h * 0.10)

    canvas = template.copy()
    canvas.alpha_composite(portrait, (paste_x, paste_y))

    # Redraw the border/banner on top so the character never occludes the frame edges.
    border_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(border_layer, "RGBA")
    margin = 18
    outer_color = _tier_color_at(tier, 0.0)
    draw.rounded_rectangle([margin, margin, w - margin, h - margin], radius=22, outline=(*outer_color, 230), width=6)
    band_top = int(h * 0.86)
    band_bot = int(h * 0.94)
    band_color = _tier_color_at(tier, 0.75)
    draw.rectangle([margin + 30, band_top, w - margin - 30, band_bot], fill=(14, 14, 16, 235), outline=(*band_color, 255), width=3)

    if hero_name:
        name_text = hero_name.upper()
        band_inner_w = (w - margin - 30) - (margin + 30) - 24
        font = _fit_name_font(draw, name_text, band_inner_w)
        bbox = draw.textbbox((0, 0), name_text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        text_x = (w - text_w) // 2 - bbox[0]
        text_y = (band_top + band_bot) // 2 - text_h // 2 - bbox[1]
        draw.text((text_x, text_y), name_text, font=font, fill=(235, 235, 235, 255))

    canvas.alpha_composite(border_layer)

    canvas.convert("RGB").save(out_path)

    # Best-effort cleanup of this hero's older cached cards (different mtime/tier).
    for f in os.listdir(CARD_CACHE_DIR):
        if f.startswith(f"{hero_id}_") and f != os.path.basename(out_path):
            try:
                os.remove(os.path.join(CARD_CACHE_DIR, f))
            except OSError:
                pass

    return out_path
