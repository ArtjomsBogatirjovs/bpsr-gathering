# autogather/waypoints.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from autogather.config import NODE_MIN_REVISIT_SEC, NODE_MERGE_RADIUS_PX


@dataclass
class Node:
    x: int
    y: int
    last_collected: float  # unix time


class WaypointDB:
    def __init__(self):
        self.nodes: List[Node] = []

    @staticmethod
    def _dist2(a: Tuple[int, int], b: Tuple[int, int]) -> int:
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return dx * dx + dy * dy

    def add_or_update(self, x: int, y: int, t: Optional[float] = None):
        """Добавить новый узел либо слить с существующим, если близко."""
        if t is None:
            t = time.time()
        pos = (x, y)
        r2 = NODE_MERGE_RADIUS_PX * NODE_MERGE_RADIUS_PX
        best_i = -1
        best_d2 = 10 ** 12
        for i, n in enumerate(self.nodes):
            d2 = self._dist2((n.x, n.y), pos)
            if d2 < best_d2:
                best_d2 = d2
                best_i = i
        if best_i >= 0 and best_d2 <= r2:
            # слить: берём среднее положение, обновляем время
            n = self.nodes[best_i]
            n.x = int((n.x + x) / 2)
            n.y = int((n.y + y) / 2)
            n.last_collected = t
        else:
            self.nodes.append(Node(x=x, y=y, last_collected=t))

    def next_available(self, curx: int, cury: int, *, remove: bool = True) -> Optional[Node]:
        """Выбрать ближайший узел, доступный по таймеру.
        Если remove=True, узел сразу удаляется из списка, чтобы не зациклиться.
        Он добавится заново при успешной добыче через add_or_update()."""
        now = time.time()
        best: Optional[Node] = None
        best_d2: float = float("inf")

        for n in self.nodes:
            if now - n.last_collected < NODE_MIN_REVISIT_SEC:
                continue
            d2 = (n.x - curx) ** 2 + (n.y - cury) ** 2
            if d2 < best_d2:
                best, best_d2 = n, d2

        if best is None:
            return None

        if remove:
            try:
                self.nodes.remove(best)
            except ValueError:
                pass

        return best
