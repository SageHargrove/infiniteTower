import os
from PIL import Image

def keep_central_cluster(img):
    try:
        datas = list(img.get_flattened_data())
    except AttributeError:
        datas = list(img.getdata())
    w, h = img.size
    
    mask = [d[3] > 0 for d in datas]
    visited = [False] * (w * h)
    components = []
    
    for i in range(w * h):
        if mask[i] and not visited[i]:
            comp = []
            q = [i]
            visited[i] = True
            
            head = 0
            while head < len(q):
                curr = q[head]
                head += 1
                comp.append(curr)
                
                cx = curr % w
                cy = curr // w
                
                if cx > 0 and mask[curr - 1] and not visited[curr - 1]:
                    visited[curr - 1] = True; q.append(curr - 1)
                if cx < w - 1 and mask[curr + 1] and not visited[curr + 1]:
                    visited[curr + 1] = True; q.append(curr + 1)
                if cy > 0 and mask[curr - w] and not visited[curr - w]:
                    visited[curr - w] = True; q.append(curr - w)
                if cy < h - 1 and mask[curr + w] and not visited[curr + w]:
                    visited[curr + w] = True; q.append(curr + w)
            
            components.append(comp)
            
    if not components:
        return img
        
    bboxes = []
    for comp in components:
        min_x = min(idx % w for idx in comp)
        max_x = max(idx % w for idx in comp)
        min_y = min(idx // w for idx in comp)
        max_y = max(idx // w for idx in comp)
        bboxes.append((min_x, min_y, max_x, max_y))
        
    jump_radius = 25
    parent = list(range(len(components)))
    
    def find(i):
        if parent[i] == i: return i
        parent[i] = find(parent[i])
        return parent[i]
        
    def union(i, j):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j
            
    for i in range(len(components)):
        for j in range(i + 1, len(components)):
            ix0, iy0, ix1, iy1 = bboxes[i]
            jx0, jy0, jx1, jy1 = bboxes[j]
            
            if not (ix1 + jump_radius < jx0 or jx1 + jump_radius < ix0 or
                    iy1 + jump_radius < jy0 or jy1 + jump_radius < iy0):
                union(i, j)
                
    merged = {}
    for i in range(len(components)):
        root = find(i)
        if root not in merged:
            merged[root] = []
        merged[root].extend(components[i])
        
    largest_cluster = max(merged.values(), key=len)
    largest_set = set(largest_cluster)
    
    newData = []
    for i in range(w * h):
        if i in largest_set:
            newData.append(datas[i])
        else:
            newData.append((0, 0, 0, 0))
            
    img.putdata(newData)
    return img


def slice_exact(img_path, vert_lines, horiz_lines, out_dir, col_names, row_names):
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(img_path).convert('RGBA')
    w, h = img.size
    
    xs = vert_lines
    ys = horiz_lines
    
    for r in range(len(row_names)):
        for c in range(len(col_names)):
            x0 = xs[c]
            y0 = ys[r]
            x1 = xs[c+1]
            y1 = ys[r+1]
            
            pad = 3
            if x1 - x0 > pad*2 and y1 - y0 > pad*2:
                cell = img.crop((x0 + pad, y0 + pad, x1 - pad, y1 - pad))
            else:
                cell = img.crop((x0, y0, x1, y1))
            
            try:
                datas = cell.get_flattened_data()
            except AttributeError:
                datas = cell.getdata()
            newData = []
            for item in datas:
                if item[0] < 10 and item[1] < 10 and item[2] < 10: 
                    newData.append((0, 0, 0, 0))
                else:
                    newData.append(item)
            cell.putdata(newData)
            
            cell = keep_central_cluster(cell)
            
            bbox = cell.getbbox()
            if bbox:
                cell = cell.crop(bbox)
            
            rarity = row_names[r]
            item_name = col_names[c]
            
            cell.save(os.path.join(out_dir, f'{item_name}_{rarity}.png'))

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw_w = os.path.join(base_dir, 'static', 'icons', '_raw', 'weapons3.png')
raw_a = os.path.join(base_dir, 'static', 'icons', '_raw', 'armor3.png')

weapons_out = os.path.join(base_dir, 'static', 'icons', 'weapons')
armor_out = os.path.join(base_dir, 'static', 'icons', 'armor')

tiers = ["legendary", "epic", "rare", "uncommon", "common", "poor", "broken"]

# Weapons
weapons_cols = ["sword", "dagger", "spear", "bow", "tome"]
w_vert = [177, 361, 544, 730, 918, 1111]
w_horiz = [49, 253, 453, 651, 848, 1026, 1197, 1379]
slice_exact(raw_w, w_vert, w_horiz, weapons_out, weapons_cols, tiers)

# Armor
armor_cols = ["light_armor", "brigandine", "heavy_armor", "robe"]
a_vert = [179, 414, 643, 872, 1106]
a_horiz = [67, 276, 472, 656, 836, 1013, 1186, 1375]
slice_exact(raw_a, a_vert, a_horiz, armor_out, armor_cols, tiers)

print("Successfully sliced and exported all icons!")
