RESOURCES_ROOT_DEFAULT = "resources"

RESOURCE_NAME_MAP = {
    "luna_ore": "Luna Ore",
    # добавляй сюда свои пары по вкусу
}

AFTER_F_SLEEP = 7.0  # сек: «копаем» после нажатия F
ACTION_COOLDOWN = 1  # сек: мин. пауза между попытками нажать F

# Матчинг подсказок
ROI_RIGHT_FRACTION = 0.50  # правая часть экрана, где живут подсказки
MATCH_THRESHOLD = 0.70
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

# Логирование совпадений
DEBUG_MATCHES = True
