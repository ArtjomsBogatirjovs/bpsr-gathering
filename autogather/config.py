RESOURCES_ROOT_DEFAULT = "resources"

RESOURCE_NAME_MAP = {
    "luna_ore": "Luna Ore",
    "baru_ore": "Baru Ore",
    "grey-top_flax": "Grey-top Flax",
    "wheat": "Wheat",
    # добавляй сюда свои пары по вкусу
}

AFTER_F_SLEEP = 7.0  # сек: «копаем» после нажатия F
ACTION_COOLDOWN = 1  # сек: мин. пауза между попытками нажать F

# ROI для подсказок [F] справа
PROMPT_ROI = (0.65, 0.49, 0.85, 0.62)  # (x1_frac, y1_frac, x2_frac, y2_frac)

# Матчинг подсказок
MATCH_THRESHOLD = 0.7
SCALES = [0.70, 0.80, 0.90, 1.00, 1.12, 1.25, 1.40]
ALIGN_TOLERANCE = 16  # допуск (px) при сравнении расстояний [F] до строк

# Скролл
SCROLL_UNIT = -120  # одно «деление» колеса (минус = вниз)
SCROLL_DELAY = 0.25  # пауза между делениями
MAX_SCROLL_STEPS = 10  # максимум шагов «медленного» скролла

# Поддерживаемые расширения картинок
IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")

# Автопоиск окна: ключевые слова в заголовке
GAME_TITLE_KEYWORDS = ("blue", "protocol", "star", "resonance", "BPSR")
REQUIRED_FOLDERS = ("focused", "gathering", "selector", "resource")

# Логирование совпадений
DEBUG_MATCHES = True

# ===== Поиск самого ресурса (объект) =====
RESOURCE_THRESHOLD = 0.8   # порог для matchTemplate на картинках ресурса
APPROACH_PAUSE     = 0.08   # пауза между шагами
APPROACH_TOLERANCE = 200     # пикселей — считаем "дошли", если ресурс почти в центре

# ===== Калибровка бега по расстоянию в пикселях =====
# Сколько миллисекунд удерживать клавишу на 1 пиксель смещения цели
MS_PER_PX_STRAFE = 1.5   # A/D — подгон по X (влево/вправо)
MS_PER_PX_FORWARD = 3  # W/S — подгон по Y (вперёд/назад)

# Ограничители, чтобы не улетать слишком далеко одним рывком
APPROACH_MIN_MS = 80       # минимум удержания
APPROACH_MAX_MS = 3000      # максимум удержания за один вызов по каждой оси

# ===== Память точек (узлов) =====
NODE_MIN_REVISIT_SEC   = 30     # мин. время, после которого узел «снова доступен»
NODE_MERGE_RADIUS_PX   = 60     # если новая точка близко к существующей — сливаем

# Калибровка наклона камеры по Y (мышью)
PITCH_OFFSET_DEFAULT = 100
PITCH_STEP_PX        = 50
PITCH_STEP_DELAY     = 0.010
