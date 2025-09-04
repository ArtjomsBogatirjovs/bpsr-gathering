from enum import Enum


class AspectRatio(Enum):
    RATIO_16_9 = (16, 9)
    RATIO_21_9 = (21, 9)
    RATIO_4_3 = (4, 3)

    @property
    def x(self):
        return self.value[0]

    @property
    def y(self):
        return self.value[1]

    def __str__(self):
        return f"{self.x}:{self.y}"