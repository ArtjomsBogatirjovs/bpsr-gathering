RESOURCES_ROOT_DEFAULT = "resources"

RESOURCE_NAME_MAP = {
    "luna_ore": "Luna Ore",
    "baru_ore": "Baru Ore",
    "grey-top_flax": "Grey-top Flax",
    "wheat": "Wheat",
    # добавляй сюда свои пары по вкусу
}

ACTION_COOLDOWN = 1  # сек: мин. пауза между попытками нажать F

# ROI для подсказок [F] справа
PROMPT_ROI = (0.65, 0.49, 0.86, 0.62)  # (x1_frac, y1_frac, x2_frac, y2_frac)

# Матчинг подсказок
MATCH_THRESHOLD = 0.7
SCALES = [0.70, 0.80, 0.90, 1.00, 1.12, 1.25, 1.40]
ALIGN_TOLERANCE = 16  # допуск (px) при сравнении расстояний [F] до строк

# Скролл
SCROLL_UNIT = -120  # одно «деление» колеса (минус = вниз)
SCROLL_DELAY = 0.25  # пауза между делениями
MAX_SCROLL_STEPS = 5  # максимум шагов «медленного» скролла

# Поддерживаемые расширения картинок
IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")

# Автопоиск окна: ключевые слова в заголовке
GAME_TITLE_KEYWORDS = ("blue", "protocol", "star", "resonance", "BPSR", "Blue", "Protocol", "Star", "Resonance",)
REQUIRED_FOLDERS = ("focused", "gathering", "selector", "resource")

# Логирование совпадений
DEBUG_MATCHES = False

# ===== Поиск самого ресурса (объект) =====
RESOURCE_THRESHOLD = 0.8   # порог для matchTemplate на картинках ресурса
APPROACH_PAUSE     = 0.08   # пауза между шагами
APPROACH_TOLERANCE_Y = 250     # пикселей — считаем "дошли", если ресурс почти в центре
APPROACH_TOLERANCE_X = 150     # пикселей — считаем "дошли", если ресурс почти в центре

# ===== Память точек (узлов) =====
NODE_MIN_REVISIT_SEC   = 31     # мин. время, после которого узел «снова доступен»
NODE_MERGE_RADIUS_PX   = 60     # если новая точка близко к существующей — сливаем
