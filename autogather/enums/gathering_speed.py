from enum import Enum

class GatheringSpeedLevel(Enum):
    SLOW = "Slow"
    NORMAL = "Normal"
    FAST = "Fast"

    def __str__(self):
        return self.value