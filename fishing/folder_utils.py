import os
import re

from fishing.config import RESOURCES_ROOT_BAITS, RESOURCE_NAME_MAP


def scan_baits():
    results = []
    if not os.path.isdir(RESOURCES_ROOT_BAITS):
        return results
    for entry in os.listdir(RESOURCES_ROOT_BAITS):
        path = os.path.join(RESOURCES_ROOT_BAITS, entry)
        if os.path.isdir(path):
            results.append((prettify_folder_name(entry), path))
    results.sort(key=lambda x: x[0].lower())
    seen = {}
    dedup = []
    for name, path in results:
        key = name.lower()
        if key in seen:
            name = f"{name} ({os.path.basename(path)})"
        seen[key] = True
        dedup.append((name, path))
    return dedup

def prettify_folder_name(name: str) -> str:
    key = name.lower()
    if key in RESOURCE_NAME_MAP:
        return RESOURCE_NAME_MAP[key]
    s = re.sub(r'[_\\-]+', ' ', name)
    parts = [p for p in s.split(' ') if p]
    return ' '.join(p.capitalize() for p in parts) if parts else name