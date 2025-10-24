import json
import os
from enum import Enum

from autogather.config import PRESET_ASPECT_RATIO
from autogather.folder_utils import _presets_path


class AspectRatio(Enum):
    RATIO_21_9 = (21, 9)
    RATIO_16_9 = (16, 9)
    RATIO_4_3 = (4, 3)

    @property
    def x(self):
        return self.value[0]

    @property
    def y(self):
        return self.value[1]

    def __str__(self):
        return f"{self.x}:{self.y}"

    @staticmethod
    def get_ratio(value: str):
        for ratio in AspectRatio:
            if str(ratio) == value:
                return ratio
        raise ValueError(f"Unknown aspect ratio: {value}")

    @staticmethod
    def from_preset():
        preset_path = _presets_path()
        if not os.path.exists(preset_path):
            return AspectRatio.RATIO_16_9

        try:
            with open(preset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(PRESET_ASPECT_RATIO)
        except Exception:
            return AspectRatio.RATIO_16_9
