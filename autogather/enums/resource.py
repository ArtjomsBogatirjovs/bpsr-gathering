from enum import Enum

DEFAULT_TOLERANCE_Y = 300
DEFAULT_TOLERANCE_X = 275


class Resource(Enum):
    ANDRA_ENIGMITE = ("andra_enigmite", 1.2, 1.1, 3, 2, True)
    BARU_ORE = ("baru_ore", 1.0, 1.0, 2, 2, True)
    BARU_RICH_ORE = ("baru_rich_ore", 1.3, 1.2, 3, 3, True)
    GREY_TOP_FLAX = ("grey-top_flax", 0.9, 1.1, 2, 1, False)
    LIMESTONE = ("limestone", 1.0, 1.0, 1, 1, False)
    LUNA_ORE = ("luna_ore", 1.1, 1.1, 2, 2, True)
    LUNA_RICH_ORE = ("luna_rich_ore", 1.2, 1.2, 3, 3, True)
    MEADOW_MUSHROOM = ("meadow_mushroom", 0.8, 1.0, 2, 2, True)
    RICH_AZTE_ORE = ("rich_azte_ore", 1.4, 1.3, 3, 3, True)
    RICH_STOKESITE_ORE = ("rich_stokesite_ore", 1.5, 1.4, 4, 4, True)
    SWEET_BERRY = ("sweet_berry", 0.7, 0.9, 1, 2, True)
    THIN_TWIG = ("thin_twig", 0.6, 0.6, 1, 1, True)
    WHEAT = ("wheat", 0.7, 0.7, 1, 1, True)

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
