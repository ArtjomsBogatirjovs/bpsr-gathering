from enum import Enum


class Direction(Enum):
    UP = (False, -1)
    DOWN = (False, 1)
    LEFT = (True, -1)
    RIGHT = (True, 1)
    NONE = (False, 0)

    def is_x(self) -> bool:
        return self.value[0]

    def get_step(self) -> int:
        return self.value[1]
