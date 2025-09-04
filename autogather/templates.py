import logging
import os

import cv2

from .config import IMG_EXTS, DEBUG_MATCHES, REQUIRED_FOLDERS

logger = logging.getLogger(__name__)

class TemplateSet:
    def __init__(self, directory: str):
        self.tmps = []
        self.directory = directory
        if os.path.isdir(directory):
            for n in os.listdir(directory):
                if n.lower().endswith(IMG_EXTS):
                    p = os.path.join(directory, n)
                    g = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
                    if g is not None and g.size > 0:
                        self.tmps.append(g)

    def best_match(self, gray_roi, scales, threshold):
        best = None
        H, W = gray_roi.shape[:2]
        for idx, g in enumerate(self.tmps):
            for s in scales:
                tw, th = int(g.shape[1] * s), int(g.shape[0] * s)
                if tw < 12 or th < 12 or tw >= W or th >= H:
                    continue
                t = cv2.resize(g, (tw, th), interpolation=cv2.INTER_AREA)
                res = cv2.matchTemplate(gray_roi, t, cv2.TM_CCOEFF_NORMED)
                _, mx, _, ml = cv2.minMaxLoc(res)

                if DEBUG_MATCHES:
                    logger.debug(
                        f"[TEMPLATE {self.directory}] scale={s:.2f} mx={mx:.3f} thr={threshold:.2f}"
                    )

                if mx >= threshold:
                    tl = (ml[0], ml[1])
                    br = (tl[0] + tw, ml[1] + th)
                    cand = {"score": float(mx), "box": (tl, br)}
                    if not best or cand["score"] > best["score"]:
                        best = cand

        if DEBUG_MATCHES:
            if best:
                logger.debug(
                    f"--> BEST score={best['score']:.3f}, box={best['box']}"
                )
            else:
                logger.debug("--> NO MATCH")

        return best
