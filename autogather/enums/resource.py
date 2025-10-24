from enum import Enum

DEFAULT_TOLERANCE_Y = 150
DEFAULT_TOLERANCE_X = 150

class Resource(Enum):
    BARU_RICH_ORE = ("baru_rich_ore", 1, 1, 200, 250, True)
    ANDRA_ENIGMITE = ("andra_enigmite", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, True)
    BARU_ORE = ("baru_ore", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, True)
    GREY_TOP_FLAX = ("grey-top_flax", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, False)
    LIMESTONE = ("limestone", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, False)
    LUNA_ORE = ("luna_ore", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, True)
    LUNA_RICH_ORE = ("luna_rich_ore", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, True)
    MEADOW_MUSHROOM = ("meadow_mushroom", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, True)
    RICH_AZTE_ORE = ("rich_azte_ore", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, True)
    RICH_STOKESITE_ORE = ("rich_stokesite_ore", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, True)
    SWEET_BERRY = ("sweet_berry", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, True)
    THIN_TWIG = ("thin_twig", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, True)
    WHEAT = ("wheat", 1, 1, DEFAULT_TOLERANCE_X, DEFAULT_TOLERANCE_Y, True)

    def __init__(self, folder: str, mult_x: float, mult_y: float,
                 tol_x: int, tol_y: int, is_focus_needed: bool = True):
        self._folder = folder
        self._mult_x = mult_x
        self._mult_y = mult_y
        self._tol_x = tol_x
        self._tol_y = tol_y
        self._is_focus_needed = is_focus_needed

    @property
    def folder_name(self):
        return self._folder

    @property
    def display_name(self) -> str:
        parts = self._folder.replace("_", " ").split()
        return " ".join(p.capitalize() for p in parts)

    def get_mult_x(self) -> float:
        return self._mult_x

    def get_mult_y(self) -> float:
        return self._mult_y

    def get_tol_x(self) -> int:
        return self._tol_x

    def get_tol_y(self) -> int:
        return self._tol_y

    @property
    def is_focus_needed(self) -> bool:
        return self._is_focus_needed

    def to_json(self) -> dict:
        return {
            "folder": self._folder,
            "mult_x": self._mult_x,
            "mult_y": self._mult_y,
            "tol_x": self._tol_x,
            "tol_y": self._tol_y,
            "want_gathering": True,
            "dont_move": False,
            "move_back_to_start": False,
            "gathering_speed": "FAST"
        }
