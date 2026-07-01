"""Slice the ChatGPT-generated rarity/type grid (static/icons/<grid_file>.png)
into individual per-item, per-rarity-tier icon files with real transparency.

Run from backend/:
    python scripts/slice_equipment_grid.py

Each cell is cropped generously then auto-trimmed to its actual content
bounding box (background color sampled per-row, since each rarity row in
the source grid has a different background tint) and the background is
keyed to alpha, same technique as generate_equipment_icons.py's
_strip_background.

Output: static/icons/weapons/<type>_<tier>.png and
static/icons/armor/<type>_<tier>.png
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

GRID_FILE = "static/icons/_raw/rarity_grid_1.png"

# top-to-bottom as they appear in the source grid
TIERS = ["legendary", "epic", "rare", "uncommon", "common", "poor", "broken"]
# left-to-right as they appear in the source grid
COLUMNS = [
    ("sword", "weapons"), ("dagger", "weapons"), ("spear", "weapons"),
    ("bow", "weapons"), ("staff", "weapons"),
    ("light_armor", "armor"), ("brigandine", "armor"),
    ("heavy_armor", "armor"), ("robe", "armor"),
]

GRID_LEFT = 150
GRID_TOP = 33
CELL_MARGIN = 6  # shrink each cell slightly so neighbor items don't bleed in

def _bg_color(img: Image.Image, box):
    """Sample a corner of the cell as the background color."""
    x0, y0, x1, y1 = box
    corner = img.crop((x0, y0, x0 + 10, y0 + 10))
    pixels = list(corner.getdata())
    n = len(pixels)
    return tuple(sum(p[i] for p in pixels) / n for i in range(3))

def _connected_content_mask(px, w, h, bg, threshold):
    """Label all connected (8-neighbor) non-background components and keep
    only the LARGEST one — the actual item — discarding smaller fragments
    bleeding in from a neighbor column (angled blades in adjacent cells
    visually overlap the grid lines in the source image). Center-seeded
    flood fill was tried first but was too fragile: thin/off-center items
    (a bow's string, a dagger not perfectly centered) could miss the seed
    region entirely and vanish."""
    from collections import deque

    def is_fg(x, y):
        r, g, b, a = px[x, y]
        dist = ((r - bg[0]) ** 2 + (g - bg[1]) ** 2 + (b - bg[2]) ** 2) ** 0.5
        return dist > threshold

    visited = [[False] * w for _ in range(h)]
    components = []

    for y0 in range(h):
        for x0 in range(w):
            if visited[y0][x0] or not is_fg(x0, y0):
                continue
            comp = []
            q = deque([(x0, y0)])
            visited[y0][x0] = True
            while q:
                x, y = q.popleft()
                comp.append((x, y))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx] and is_fg(nx, ny):
                        visited[ny][nx] = True
                        q.append((nx, ny))
            components.append(comp)

    if not components:
        return [[False] * w for _ in range(h)]

    largest = max(components, key=len)
    mask = [[False] * w for _ in range(h)]
    for x, y in largest:
        mask[y][x] = True
    return mask

def _trim_and_key(img: Image.Image, box, threshold=38, feather=30) -> Image.Image:
    x0, y0, x1, y1 = box
    cell = img.crop((x0 + CELL_MARGIN, y0 + CELL_MARGIN, x1 - CELL_MARGIN, y1 - CELL_MARGIN)).convert("RGBA")
    bg = _bg_color(img, box)

    w, h = cell.size
    px = cell.load()

    mask = _connected_content_mask(px, w, h, bg, threshold)

    min_x, min_y, max_x, max_y = w, h, 0, 0
    found = False
    for y in range(h):
        for x in range(w):
            if mask[y][x]:
                found = True
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)
            else:
                # zero out anything not connected to the centered item —
                # this is what actually removes neighbor bleed
                r, g, b, a = px[x, y]
                px[x, y] = (r, g, b, 0)

    if not found or max_x <= min_x or max_y <= min_y:
        # nothing detected — bail out with the un-trimmed, un-keyed cell
        return cell

    pad = 6
    min_x, min_y = max(0, min_x - pad), max(0, min_y - pad)
    max_x, max_y = min(w, max_x + pad), min(h, max_y + pad)
    cropped = cell.crop((min_x, min_y, max_x, max_y))

    # key background to alpha on the cropped result — pixels already
    # zeroed above (disconnected neighbor-bleed) are skipped so this pass
    # doesn't resurrect them just because their color happens to be far
    # from this cell's background color.
    cw, ch = cropped.size
    cpx = cropped.load()
    for y in range(ch):
        for x in range(cw):
            r, g, b, a = cpx[x, y]
            if a == 0:
                continue
            dist = ((r - bg[0]) ** 2 + (g - bg[1]) ** 2 + (b - bg[2]) ** 2) ** 0.5
            if dist < threshold:
                cpx[x, y] = (r, g, b, 0)
            elif dist < threshold + feather:
                cpx[x, y] = (r, g, b, int(255 * (dist - threshold) / feather))
    return cropped

def slice_all():
    img = Image.open(GRID_FILE).convert("RGB")
    w, h = img.size
    col_w = (w - GRID_LEFT) / len(COLUMNS)
    row_h = (h - GRID_TOP) / len(TIERS)

    for r, tier in enumerate(TIERS):
        for c, (item_name, subdir) in enumerate(COLUMNS):
            x0 = GRID_LEFT + c * col_w
            y0 = GRID_TOP + r * row_h
            x1 = x0 + col_w
            y1 = y0 + row_h
            result = _trim_and_key(img, (x0, y0, x1, y1))
            out_dir = f"static/icons/{subdir}"
            os.makedirs(out_dir, exist_ok=True)
            out_path = f"{out_dir}/{item_name}_{tier}.png"
            result.save(out_path)
            print(f"  {out_path}  ({result.size[0]}x{result.size[1]})")

if __name__ == "__main__":
    slice_all()
