import cv2
from .config import ROI_RIGHT_FRACTION
from .templates import TemplateSet

def debug_snapshot(frame_bgr, ts_f: TemplateSet, ts_g: TemplateSet, ts_s: TemplateSet,
                   scales, threshold, outfile="debug_prompt.png"):
    """Рисует рамки для лучшего совпадения каждого типа и сохраняет картинку."""
    gray  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    h, w  = gray.shape[:2]
    x0    = int(w * (1.0 - ROI_RIGHT_FRACTION))
    roi   = gray[:, x0:]

    def draw(ts, color):
        if not ts or not ts.tmps:
            return None
        hit = ts.best_match(roi, scales, threshold)
        if hit:
            (x1,y1),(x2,y2) = hit["box"]
            cv2.rectangle(frame_bgr, (x0+x1, y1), (x0+x2, y2), color, 2)
        return hit

    hf = draw(ts_f, (0,255,0))
    hg = draw(ts_g, (255,0,0))
    hs = draw(ts_s, (0,255,255))
    cv2.rectangle(frame_bgr, (x0,0), (w,h), (200,200,0), 2)  # ROI
    cv2.imwrite(outfile, frame_bgr)

    return {"Focused": bool(hf), "Gathering": bool(hg), "[F]": bool(hs), "file": outfile}
