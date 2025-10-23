import logging
import os

import cv2

logger = logging.getLogger(__name__)

def save_roi_debug(frame, roi_coords, filename="roi_debug.png"):
    """
    Сохраняет картинку с обведённым ROI в файл.
    """
    (x1, y1, x2, y2) = roi_coords
    dbg = frame.copy()
    cv2.rectangle(dbg, (x1, y1), (x2, y2), (0, 255, 0), 2)  # зелёный прямоугольник

    out_path = os.path.abspath(filename)
    ok = cv2.imwrite(out_path, dbg)
    if ok:
        logger.debug(f"ROI debug saved: {out_path}")
    else:
        logger.error(f"Failed to save ROI debug: {out_path}")


