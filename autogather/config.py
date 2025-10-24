RESOURCES_ROOT_DEFAULT = "resources"

ACTION_COOLDOWN = 1

PROMPT_ROI = (0.65, 0.49, 0.86, 0.62)  # (x1_frac, y1_frac, x2_frac, y2_frac)

MATCH_THRESHOLD = 0.7
SCALES = [0.70, 0.80, 0.90, 1.00, 1.12, 1.25, 1.40]
ALIGN_TOLERANCE = 16

SCROLL_UNIT = -120
SCROLL_DELAY = 0.25
MAX_SCROLL_STEPS = 5

IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")

GAME_TITLE_KEYWORDS = ("blue", "protocol", "star", "resonance", "BPSR", "Blue", "Protocol", "Star", "Resonance",)
REQUIRED_FOLDERS = ("focused", "gathering", "selector", "resource")

RESOURCE_THRESHOLD = 0.8
APPROACH_PAUSE = 0.08

NODE_MIN_REVISIT_SEC = 30
NODE_MERGE_RADIUS_PX = 50

PRESET_ASPECT_RATIO = "aspect_ratio"
PRESET_MULT_X = "mult_x"
PRESET_MULT_Y = "mult_y"
PRESET_TOL_X = "tol_x"
PRESET_TOL_Y = "tol_y"
PRESET_WANT_GATHERING = "want_gathering"
PRESET_DONT_MOVE = "dont_move"
PRESET_MOVE_BACK_TO_START = "move_back_to_start"
PRESET_SPEED = "gathering_speed"