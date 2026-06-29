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
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CANVAS_SIZE = (700, 1050)
TEMPLATE_DIR = os.path.join("static", "card_templates")
CARD_CACHE_DIR = os.path.join("static", "portraits", "cards")

# No local copy of the app's actual web font (Cinzel is loaded from Google
# Fonts at runtime, not bundled as a file) — Georgia Bold is a close-enough
# elegant serif already present on Windows, so no new asset/download needed.
_NAME_FONT_PATH = r"C:\Windows\Fonts\georgiab.ttf"
_EMOJI_FONT_PATH = r"C:\Windows\Fonts\seguiemj.ttf"


def _name_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(_NAME_FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _emoji_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_EMOJI_FONT_PATH, size)

# One tier per star (was bucketed 1-2/3-4/5-6/7, which made 1*/2* and 5*/6*
# cards indistinguishable — directly against the "5*+ should look
# dramatically different, the 4*->5* gap should feel like a qualitative
# leap" requirement). "obsidian" (6*) gets its own _build_template branch
# below rather than just another flat color, since a color swap alone
# isn't a "visually distinct... not just a color swap" design.
TIER_COLORS = {
    "iron":      (138, 138, 138),  # 1* — brushed steel grey, thin/understated
    "bronze":    (140, 78, 38),    # 2* — deep copper-brown
    "silver":    (196, 200, 212),  # 3*
    "gold":      (224, 170, 30),   # 4* — vivid yellow-gold
    "amethyst":  (155, 48, 255),   # 5* — deep purple, glow added in _build_template
    "obsidian":  (201, 36, 36),    # 6* — crimson accent against a near-black base; ornate, not just a color
    "prismatic": None,  # 7* — rainbow gradient, handled specially
}

# Tiers from here up get glow/shimmer treatment 1-4* deliberately don't —
# "no glow or shimmer effects SHALL be applied to 1-4* cards".
GLOW_TIERS = {"amethyst", "obsidian", "prismatic"}

PRISMATIC_HUES = [(255, 60, 60), (255, 200, 60), (80, 220, 120), (60, 180, 255), (180, 90, 255)]


def tier_for_star(birth_star: int) -> str:
    return {1: "iron", 2: "bronze", 3: "silver", 4: "gold", 5: "amethyst", 6: "obsidian"}.get(birth_star, "prismatic" if birth_star >= 7 else "iron")


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


def _build_template(tier: str) -> Image.Image:
    w, h = CANVAS_SIZE
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    margin = 18

    # Glow halo for 5*/6*/7* — a blurred, oversized copy of the border drawn
    # underneath the sharp one, which is what actually reads as "luminous"
    # rather than just a brighter flat color. 1-4* skip this entirely.
    if tier in GLOW_TIERS:
        glow_color = _tier_color_at(tier, 0.0)
        glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer, "RGBA")
        glow_draw.rounded_rectangle([margin, margin, w - margin, h - margin], radius=22, outline=(*glow_color, 255), width=14)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(10))
        img.alpha_composite(glow_layer)

    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = w // 2, int(h * 0.42)

    # Outer ornate border — double rounded-rect outline + corner diamonds.
    outer_color = _tier_color_at(tier, 0.0)
    draw.rounded_rectangle([margin, margin, w - margin, h - margin], radius=22, outline=(*outer_color, 230), width=6)
    draw.rounded_rectangle([margin + 14, margin + 14, w - margin - 14, h - margin - 14], radius=16, outline=(*outer_color, 140), width=2)

    diamond_r = 10
    for dx, dy in [(margin, margin), (w - margin, margin), (margin, h - margin), (w - margin, h - margin)]:
        diamond_color = _tier_color_at(tier, 0.25)
        draw.polygon([(dx, dy - diamond_r), (dx + diamond_r, dy), (dx, dy + diamond_r), (dx - diamond_r, dy)], fill=(*diamond_color, 255))

    # Obsidian (6*) gets rune-like tick marks along the border on top of the
    # crimson color — a structural difference, not just another color swap,
    # per "visually distinct from all other tiers (not just a color swap)".
    if tier == "obsidian":
        tick_color = (40, 10, 10, 255)
        n_ticks = 18
        for i in range(n_ticks):
            t = i / n_ticks
            x = margin + t * (w - 2 * margin)
            draw.line([(x, margin + 3), (x, margin + 11)], fill=tick_color, width=2)
            draw.line([(x, h - margin - 3), (x, h - margin - 11)], fill=tick_color, width=2)

    # Prismatic (7*) gets a corner glyph label, per spec — the rainbow
    # border alone might not be enough at a glance to read as the top tier.
    if tier == "prismatic":
        glyph_font = _name_font(16)
        draw.text((margin + 22, margin + 6), "✦ PRISMATIC", font=glyph_font, fill=(255, 255, 255, 235))

    # Nameplate banner near the bottom
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
    return Image.open(path).convert("RGBA")





def _draw_star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color: tuple):
    """Hand-drawn 5-point star polygon — the emoji font's "*" glyph isn't
    guaranteed to exist (renders as a tofu box on this system's Segoe UI
    Emoji), so this draws the shape directly instead of depending on font
    glyph coverage, same robustness approach already used for the corner
    diamond accents below."""
    import math
    points = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        radius = r if i % 2 == 0 else r * 0.4
        points.append((cx + radius * math.cos(angle), cy - radius * math.sin(angle)))
    draw.polygon(points, fill=(*color, 255))


def _fit_name_font(draw: ImageDraw.ImageDraw, name: str, max_width: int, max_size: int = 52, min_size: int = 18) -> ImageFont.FreeTypeFont:
    size = max_size
    while size > min_size:
        font = _name_font(size)
        bbox = draw.textbbox((0, 0), name, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 2
    return _name_font(min_size)


def composite_card(hero_id: int, portrait_path: str, birth_star: int, hero_name: str = "", crop_face: bool = False, hero_class: str = "") -> str:
    """Builds (or returns the cached) composited card image path for a hero.
    Cache key includes the portrait file's mtime (so a regenerated/rerolled
    portrait invalidates the old composited card) and a hash of the name (so
    a late-arriving LLM-enriched name also invalidates it).

    crop_face=True builds a face-focused variant instead of the full
    head-to-chest card — for small grid thumbnails, where fitting the whole
    body into a tiny box means the face (the part anyone's actually looking
    at) gets a much harder downscale than necessary. Cropping tighter first
    means the face occupies more of the same pixel budget, which reads as
    noticeably less blurry at thumbnail size. Cached separately (different
    filename tag) alongside the full variant, not in place of it — the
    expanded/full view still wants the complete card."""
    os.makedirs(CARD_CACHE_DIR, exist_ok=True)
    tier = tier_for_star(birth_star)
    mtime = int(os.path.getmtime(portrait_path))
    name_hash = abs(hash((hero_name, hero_class))) % 100000
    variant = "mini" if crop_face else "full"
    out_path = os.path.join(CARD_CACHE_DIR, f"{hero_id}_{variant}_{tier}_{mtime}_{name_hash}.png")
    if os.path.exists(out_path):
        return out_path

    template = get_template(tier).convert("RGBA")
    portrait = Image.open(portrait_path).convert("RGBA")

    if crop_face:
        # Keep the top ~80% (full face through chin/neck, cropping out just
        # the lower shoulders/chest) and zoom that into the same frame area
        # the full card uses for the entire head-to-chest composition.
        # NOTE: a tighter 58% crop was tried first and cut faces off at the
        # mouth/chin on several real portraits — composition (how much
        # headroom/hair sits above the face) varies enough between
        # generations that a fixed crop needs real margin, not a precise gust.
        crop_h = int(portrait.height * 0.80)
        portrait = portrait.crop((0, 0, portrait.width, crop_h))

    w, h = template.size

    # Crop to fill aspect ratio
    target_ratio = w / h
    port_ratio = portrait.width / portrait.height
    if port_ratio > target_ratio:
        new_w = int(target_ratio * portrait.height)
        offset = (portrait.width - new_w) // 2
        portrait = portrait.crop((offset, 0, offset + new_w, portrait.height))
    else:
        new_h = int(portrait.width / target_ratio)
        offset = (portrait.height - new_h) // 2
        portrait = portrait.crop((0, offset, portrait.width, offset + new_h))

    portrait = portrait.resize((w, h), Image.LANCZOS)
    canvas = portrait.copy()
    canvas.alpha_composite(template, (0, 0))

    # Add class icon and name text over the border
    draw = ImageDraw.Draw(canvas, "RGBA")
    margin = 18

    # Star row — exactly birth_star icons, positioned above the class
    # medallion so neither overlaps the portrait face below. Uses the emoji
    # font since Georgia Bold's "*" glyph reads as a tiny asterisk, not a
    # filled star.
    cx = w // 2
    star_y = margin + 18
    star_spacing = 24
    total_w = star_spacing * max(0, birth_star - 1)
    start_x = cx - total_w / 2
    for i in range(birth_star):
        sx = start_x + i * star_spacing
        _draw_star(draw, sx, star_y, 9, _tier_color_at(tier, 0.5))

    # Class icon medallion at the top — 2-letter abbreviation in Georgia Bold,
    # guaranteed crisp on all classes including Classless.
    from services.class_service import get_class_abbrev
    icon_y = margin + 56
    icon_color = _tier_color_at(tier, 0.6)
    draw.ellipse([cx - 28, icon_y - 28, cx + 28, icon_y + 28], fill=(20, 20, 24, 255), outline=(*icon_color, 255), width=4)
    abbrev = get_class_abbrev(hero_class)
    abbrev_font = _name_font(17)
    bbox = draw.textbbox((0, 0), abbrev, font=abbrev_font)
    glyph_cx = (bbox[0] + bbox[2]) / 2
    glyph_cy = (bbox[1] + bbox[3]) / 2
    draw.text((cx - glyph_cx, icon_y - glyph_cy), abbrev, font=abbrev_font, fill=(*icon_color, 255))


    band_top = int(h * 0.86)
    band_bot = int(h * 0.94)
    if hero_name:
        name_text = hero_name.upper()
        band_inner_w = (w - margin - 30) - (margin + 30) - 24
        font = _fit_name_font(draw, name_text, band_inner_w)
        bbox = draw.textbbox((0, 0), name_text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        text_x = (w - text_w) // 2 - bbox[0]
        text_y = (band_top + band_bot) // 2 - text_h // 2 - bbox[1]
        draw.text((text_x, text_y), name_text, font=font, fill=(235, 235, 235, 255))

    # Mask everything outside the rounded rectangle to be fully transparent
    mask = Image.new('L', (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([margin, margin, w - margin, h - margin], radius=22, fill=255)
    canvas.putalpha(mask)

    canvas.save(out_path, format="PNG")

    # Best-effort cleanup of this hero's older cached cards for THIS SAME
    # variant (different mtime/tier) — must not touch the other variant's
    # cache file, since both a full and mini card are cached side by side.
    stale_prefix = f"{hero_id}_{variant}_"
    for f in os.listdir(CARD_CACHE_DIR):
        if f.startswith(stale_prefix) and f != os.path.basename(out_path):
            try:
                os.remove(os.path.join(CARD_CACHE_DIR, f))
            except OSError:
                pass

    return out_path
