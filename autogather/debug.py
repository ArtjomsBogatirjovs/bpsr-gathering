import logging
import os

import cv2

logger = logging.getLogger(__name__)


def save_selector_debug(frame, roi_coords, filename="selector_rectangle.png"):
    (x1, y1, x2, y2) = roi_coords
    dbg = frame.copy()
    cv2.rectangle(dbg, (x1, y1), (x2, y2), (0, 255, 0), 2)

    out_path = os.path.abspath(filename)
    ok = cv2.imwrite(out_path, dbg)
    if ok:
        logger.debug(f"Selector debug saved: {out_path}")
    else:
        logger.error(f"Failed to save selector debug: {out_path}")
