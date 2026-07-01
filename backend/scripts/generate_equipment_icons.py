"""Generate one item-icon image per weapon_type/armor_type via the same
local ComfyUI pipeline used for hero portraits (services/comfy_service.py).

Requires ComfyUI running locally (COMFY_URL in comfy_service.py, default
http://127.0.0.1:8188) with the checkpoint already configured. Run from
backend/:

    python scripts/generate_equipment_icons.py

Outputs land in static/icons/weapons/<slug>.png and static/icons/armor/<slug>.png
— the frontend (InventoryPage.jsx) looks for these by the same slug and
falls back to an emoji if a file isn't there yet, so it's safe to run this
for a subset of types (e.g. re-rolling just one) without breaking the rest.

NOTE on the approach (three earlier attempts failed before this one):
1. "item icon, game asset, white background" — the checkpoint (NoobAI-XL,
   a character/portrait-trained model, not an icon-pack model) read
   "icon"/"game asset" as a literal mobile-game UI icon and hallucinated
   shield/banner/badge compositions unrelated to the actual item.
2. "fantasy concept art, painted illustration, ornate, standing upright" —
   pulled toward decorative-object associations (candelabras, trophies,
   fleur-de-lis finials) instead of an actual weapon.
3. "manhwa style, dynamic action illustration" alone (txt2img) — produced
   sparse, off-center action-panel framing with the weapon shoved into a
   corner of mostly blank canvas.
The common root cause: this checkpoint has very little "isolated
weapon/armor floating in a void" training data — it's almost all
character art, so without a character anchoring the composition it
free-associates. Fix: stop asking it to invent the composition. A simple
correct silhouette (see _silhouettes.py, plain PIL shapes) is fed in as an
img2img reference at denoise ~0.78 — high enough that the checkpoint fully
repaints style/shading/glow in its own manhwa look, low enough that the
silhouette still pins down the actual shape.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.comfy_service import generate_portrait_comfy, is_comfy_running
from _silhouettes import SILHOUETTES

# Optional dedicated LoRA for item/equipment generation — separate from
# whatever COMFY_LORA is configured for hero portraits, so turning this on
# doesn't change portrait generation. Set ICON_LORA to the .safetensors
# filename as it appears in ComfyUI/models/loras/ once you've got one (e.g.
# an Illustrious-compatible "weapon"/"isolated item" LoRA from CivitAI).
ICON_LORA = os.getenv("ICON_LORA", None)
ICON_LORA_STRENGTH = float(os.getenv("ICON_LORA_STRENGTH", "0.8"))

NEGATIVE = (
    "humans, person, people, character, hands, fingers, body, face, mannequin, "
    "candelabra, candlestick, chalice, goblet, trophy, vase, urn, fleur de lis, "
    "icon, vector art, flat design, clip art, logo, emblem, badge, banner, shield, "
    "ui element, app icon, frame, border, multiple objects, collage, grid, comic panel, "
    "blurry, low quality, watermark, text, signature, bad anatomy, deformed, "
    "worst quality, jpeg artifacts"
)

# "fantasy concept art / ornate / standing upright" kept pulling the
# checkpoint toward decorative-object associations (candelabras, trophies,
# fleur-de-lis finials) instead of an actual weapon — apparently stronger
# training signal for "ornate isolated object" than for "weapon" alone.
# Manhwa/webtoon action-art tags pull from a much deeper well of actual
# weapon panels (this is an anime/manhwa-tag-trained checkpoint), so lean
# into that instead of a generic "concept art" framing.
STYLE_SUFFIX = (
    ", manhwa style, korean webtoon art style, dynamic action illustration, "
    "glowing magic effect, black background, no humans, no character, "
    "single weapon, detailed line art, high quality"
)

WEAPON_PROMPTS = {
    "Sword": "a glowing fantasy sword, sharp longsword blade, dark hilt",
    # "glowing spearhead" made the whole shaft read as a beam/laser of
    # light instead of a solid weapon — dropped the glow, emphasized solid
    # wood/metal material instead.
    "Spear": "a fantasy spear, solid wooden shaft, sharp steel spearhead, sturdy and heavy, metallic sheen",
    "Staff": "a fantasy magic staff with a glowing crystal orb",
    # was reading as flat/plain — more material and craft detail
    "Bow": "an ornate carved wooden recurve bow, strung, polished wood grain, fantasy hunting weapon, detailed craftsmanship",
    # came out sword-sized — daggers need to read as obviously SHORT and
    # stubby, not just a small sword. Explicit comparison + no crossguard.
    "Dagger": "a short fantasy dagger, much shorter than a sword, wide stubby blade, simple grip, no crossguard, easily concealed",
}

# Armor went through two bad rounds: first "glowing energy lines/accents"
# overpowered the silhouette into blade/gem shapes; then dropping denoise
# to 0.65 to fix that left it basically unrendered — just the flat PIL
# placeholder smoothed slightly, with zero real material/shading (and on
# Light Armor, the two glowing accent dots got read as eyes on the
# vest's face-shaped silhouette). Fix: denoise back up so the checkpoint
# actually repaints, material/lighting language instead of glow language,
# and an explicit negative against eyes/face since that's what bit us.
ARMOR_PROMPTS = {
    "Heavy Armor": "a suit of fantasy heavy steel plate armor, thick metal chest piece with shoulder pauldrons, polished metal sheen, battle-worn dents and scratches, dramatic rim lighting",
    "Brigandine": "a fantasy leather and metal brigandine armor chest piece with shoulder guards, studded metal rivets over worn leather, dramatic rim lighting",
    "Light Armor": "a fantasy leather armor chest piece with shoulder guards, light rogue's protective gear, supple worn leather texture, dramatic rim lighting",
    "Robe": "a fantasy hooded mage's robe, flowing dark fabric with ornate gold embroidery trim, rich cloth texture, dramatic rim lighting",
}

ARMOR_NEGATIVE_FACE = ", eyes, face, mask, eyeballs"

ARMOR_NEGATIVE_EXTRA = (
    ", weapon, sword, blade, dagger, knife, spear, gem, crystal, diamond, "
    "flame, fire, feather, wing, abstract"
)

def _slug(name: str) -> str:
    return name.lower().replace(" ", "_")

def _strip_background(path: str, threshold: int = 50, feather: int = 40):
    """Key out the solid-black backdrop to real alpha transparency. Samples
    the four corners (not just pure black) since the model's 'solid black
    background' instruction still comes back with slight gradient/noise —
    sampling lets this adapt instead of assuming an exact (0,0,0)."""
    from PIL import Image
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    px = img.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    bg = tuple(sum(c[i] for c in corners) / 4 for i in range(3))
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            dist = ((r - bg[0]) ** 2 + (g - bg[1]) ** 2 + (b - bg[2]) ** 2) ** 0.5
            if dist < threshold:
                px[x, y] = (r, g, b, 0)
            elif dist < threshold + feather:
                px[x, y] = (r, g, b, int(255 * (dist - threshold) / feather))
    img.save(path)

def _generate_one(name: str, prompt: str, save_path: str, denoise: float = 0.78, extra_negative: str = ""):
    print(f"Generating {name} -> {save_path}")

    import tempfile
    ref_path = os.path.join(tempfile.gettempdir(), f"_silhouette_{_slug(name)}.png")
    SILHOUETTES[name]().save(ref_path)

    ok = generate_portrait_comfy(
        prompt + STYLE_SUFFIX, save_path,
        init_image_path=ref_path, denoise=denoise,
        negative=NEGATIVE + extra_negative, width=768, height=768,
        lora_override=ICON_LORA, lora_strength_override=ICON_LORA_STRENGTH,
    )
    if not ok:
        print("  FAILED")
        return
    try:
        _strip_background(save_path)
        print("  ok (background removed)")
    except Exception as e:
        print(f"  generated but background removal failed: {e}")

def generate_all():
    if not is_comfy_running():
        print("[ComfyUI] Server not running at the configured COMFY_URL — start ComfyUI first.")
        return

    for weapon_type, prompt in WEAPON_PROMPTS.items():
        _generate_one(weapon_type, prompt, f"static/icons/weapons/{_slug(weapon_type)}.png")

    for armor_type, prompt in ARMOR_PROMPTS.items():
        _generate_one(armor_type, prompt, f"static/icons/armor/{_slug(armor_type)}.png", denoise=0.65, extra_negative=ARMOR_NEGATIVE_EXTRA)

if __name__ == "__main__":
    generate_all()
