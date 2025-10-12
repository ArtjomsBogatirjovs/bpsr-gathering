RESOURCES_ROOT_DEFAULT = "resources"





# ROI для подсказок [F] справа
PROMPT_ROI = (0.65, 0.49, 0.86, 0.62)  # (x1_frac, y1_frac, x2_frac, y2_frac)

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
GAME_TITLE_KEYWORDS = ("blue", "protocol", "star", "resonance", "BPSR", "Blue", "Protocol", "Star", "Resonance",)