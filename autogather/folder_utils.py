import os
from typing import List, Dict

from autogather.config import RESOURCES_ROOT_DEFAULT, REQUIRED_FOLDERS
from autogather.enums.resource import Resource
from autogather.model.templates import TemplateSet

FOLDER_TO_RESOURCE: Dict[str, Resource] = {r.folder_name: r for r in Resource}


def scan_resources() -> List[Resource]:
    results: List[Resource] = []

    if not os.path.isdir(RESOURCES_ROOT_DEFAULT):
        return results

    for entry in os.listdir(RESOURCES_ROOT_DEFAULT):
        path = os.path.join(RESOURCES_ROOT_DEFAULT, entry)

        if os.path.isdir(path):
            res = FOLDER_TO_RESOURCE.get(entry)
            if res and resource_has_required_folders(path, res):
                results.append(res)
            else:
                print(f"[scan_resources] folder has no matching Enum value: {entry}")
    return results


def resource_has_required_folders(resource_dir: str, res: Resource) -> bool:
    if not os.path.isdir(resource_dir): return False
    for i in REQUIRED_FOLDERS:
        if i == REQUIRED_FOLDERS[0] and not res.is_focus_needed: continue
        temp_dir = os.path.join(resource_dir, i)
        if not temp_dir:
            return False
    return True


def load_resource_dir(resource_dir: str, res: Resource):
    resource_dir = RESOURCES_ROOT_DEFAULT + "/" + resource_dir
    if not os.path.isdir(resource_dir):
        raise FileNotFoundError(f"Resource folder not found: {resource_dir}")
    dir_f = _pick_subdir(resource_dir, REQUIRED_FOLDERS[0])
    dir_g = _pick_subdir(resource_dir, REQUIRED_FOLDERS[1])
    dir_s = _pick_subdir(resource_dir, REQUIRED_FOLDERS[2])
    dir_r = _pick_subdir(resource_dir, REQUIRED_FOLDERS[3])
    missing = []
    if not dir_f and res.is_focus_needed: missing.append(REQUIRED_FOLDERS[0] + "/")
    if not dir_g: missing.append(REQUIRED_FOLDERS[1] + "/")
    if not dir_s: missing.append(REQUIRED_FOLDERS[2] + "/")
    if not dir_r: missing.append(REQUIRED_FOLDERS[3] + "/")
    if missing:
        raise FileNotFoundError(f"In {resource_dir} no subfolders: {', '.join(missing)}")
    return TemplateSet(dir_f), TemplateSet(dir_g), TemplateSet(dir_s), TemplateSet(dir_r)


def _pick_subdir(resource_dir: str, *alts):
    names = {n.lower(): os.path.join(resource_dir, n)
             for n in os.listdir(resource_dir)
             if os.path.isdir(os.path.join(resource_dir, n))}
    for a in alts:
        if a in names:
            return names[a]
    return None
