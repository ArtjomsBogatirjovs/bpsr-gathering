import os, re
import cv2
from .config import IMG_EXTS, RESOURCE_NAME_MAP

def _pick_subdir(resource_dir: str, *alts):
    names = {n.lower(): os.path.join(resource_dir, n)
             for n in os.listdir(resource_dir)
             if os.path.isdir(os.path.join(resource_dir, n))}
    for a in alts:
        if a in names:
            return names[a]
    return None

def resource_has_required_folders(resource_dir: str) -> bool:
    if not os.path.isdir(resource_dir): return False
    dir_f = _pick_subdir(resource_dir, "focused","focus","f")
    dir_g = _pick_subdir(resource_dir, "gathering","gather","g")
    dir_s = _pick_subdir(resource_dir, "selector","select","sel","f_key","fkey","f-icon","ficon")
    return all([dir_f, dir_g, dir_s])

def prettify_folder_name(name: str) -> str:
    key = name.lower()
    if key in RESOURCE_NAME_MAP:
        return RESOURCE_NAME_MAP[key]
    s = re.sub(r'[_\-]+', ' ', name)
    parts = [p for p in s.split(' ') if p]
    return ' '.join(p.capitalize() for p in parts) if parts else name

def scan_resources(root_dir: str):
    """Сканирует корень и возвращает список (display_name, absolute_path)."""
    results = []
    if not os.path.isdir(root_dir):
        return results
    for entry in os.listdir(root_dir):
        path = os.path.join(root_dir, entry)
        if os.path.isdir(path) and resource_has_required_folders(path):
            results.append((prettify_folder_name(entry), path))
    # сортировка + дедуп имен
    results.sort(key=lambda x: x[0].lower())
    seen = {}
    dedup = []
    for name, path in results:
        base = os.path.basename(path)
        key = name.lower()
        if key in seen:
            name = f"{name} ({base})"
        seen[key] = True
        dedup.append((name, path))
    return dedup

class TemplateSet:
    """Набор шаблонов (много файлов)."""
    def __init__(self, directory: str):
        self.tmps = []
        if os.path.isdir(directory):
            for n in os.listdir(directory):
                if n.lower().endswith(IMG_EXTS):
                    p = os.path.join(directory, n)
                    g = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
                    if g is not None and g.size > 0:
                        self.tmps.append(g)

    def best_match(self, gray_roi, scales, threshold):
        """Лучшее совпадение: dict {'score', 'box': ((x1,y1),(x2,y2))} или None."""
        import cv2  # локально для headless-режима
        best = None
        H, W = gray_roi.shape[:2]
        for g in self.tmps:
            for s in scales:
                tw, th = int(g.shape[1]*s), int(g.shape[0]*s)
                if tw < 12 or th < 12 or tw >= W or th >= H:
                    continue
                t = cv2.resize(g, (tw, th), interpolation=cv2.INTER_AREA)
                res = cv2.matchTemplate(gray_roi, t, cv2.TM_CCOEFF_NORMED)
                _, mx, _, ml = cv2.minMaxLoc(res)
                if mx >= threshold:
                    tl = (ml[0], ml[1])
                    br = (tl[0]+tw, tl[1]+th)
                    cand = {"score": float(mx), "box": (tl, br)}
                    if not best or cand["score"] > best["score"]:
                        best = cand
        return best

def load_resource_dir(resource_dir: str):
    """Возвращает три TemplateSet: (focused, gathering, selector)."""
    if not os.path.isdir(resource_dir):
        raise FileNotFoundError(f"Папка ресурса не найдена: {resource_dir}")
    dir_f = _pick_subdir(resource_dir, "focused","focus","f")
    dir_g = _pick_subdir(resource_dir, "gathering","gather","g")
    dir_s = _pick_subdir(resource_dir, "selector","select","sel","f_key","fkey","f-icon","ficon")
    missing = []
    if not dir_f: missing.append("focused/")
    if not dir_g: missing.append("gathering/")
    if not dir_s: missing.append("selector/")
    if missing:
        raise FileNotFoundError(f"В {resource_dir} нет подпапок: {', '.join(missing)}")
    return TemplateSet(dir_f), TemplateSet(dir_g), TemplateSet(dir_s)
