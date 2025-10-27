from autogather.enums.direction import Direction


class ResourceObject:
    def __init__(
            self,
            folder: str,
            mult_x: float,
            mult_y: float,
            tol_x: int,
            tol_y: int,
            is_focus_needed: bool = True,
            adjust_every_cycle: bool = False,
            adjust_dir: Direction = Direction.NONE
    ):
        self.folder = folder
        self.mult_x = mult_x
        self.mult_y = mult_y
        self.tol_x = tol_x
        self.tol_y = tol_y
        self.is_focus_needed = is_focus_needed
        self.adjust_dir = adjust_dir
        self.adjust_every_cycle = adjust_every_cycle
        print("[Resource] Created:", self)

    @property
    def display_name(self) -> str:
        parts = self.folder.replace("_", " ").split()
        return " ".join(p.capitalize() for p in parts)

    def get_mult_x(self) -> float:
        return self.mult_x

    def get_mult_y(self) -> float:
        return self.mult_y

    def get_tol_x(self) -> int:
        return self.tol_x

    def get_tol_y(self) -> int:
        return self.tol_y

    def is_adjust_every_cycle(self) -> bool:
        return self.adjust_every_cycle

    def get_adjust_dir(self) -> Direction:
        return self.adjust_dir

    def __repr__(self):
        return (
            f"Resource(folder='{self.folder}', "
            f"mult_x={self.mult_x}, mult_y={self.mult_y}, "
            f"tol_x={self.tol_x}, tol_y={self.tol_y}, "
            f"is_focus_needed={self.is_focus_needed})"
        )
