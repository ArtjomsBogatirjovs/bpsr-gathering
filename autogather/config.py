# Корень с наборами ресурсов (каждая папка = один ресурс)
RESOURCES_ROOT_DEFAULT = "resources"

# "Enum"-маппинг: имя папки (lowercase) -> красивое имя
RESOURCE_NAME_MAP = {
    "luna_ore": "Luna Ore",
    "luna-ore": "Luna Ore",
    "lunaore":  "Luna Ore",
    # добавляй сюда свои пары по вкусу
}

# Паузы/кулдауны
AFTER_F_SLEEP   = 6.0   # сек: «копаем» после нажатия F
ACTION_COOLDOWN = 0.8   # сек: мин. пауза между попытками нажать F

# Матчинг подсказок
ROI_RIGHT_FRACTION = 0.50   # правая часть экрана, где живут подсказки
MATCH_THRESHOLD    = 0.56
SCALES             = [0.70,0.80,0.90,1.00,1.12,1.25,1.40]
ALIGN_TOLERANCE    = 16     # допуск (px) при сравнении расстояний [F] до строк

# Скролл
SCROLL_UNIT  = -120   # одно «деление» колеса (минус = вниз)
SCROLL_DELAY = 0.25   # пауза между делениями
MAX_SCROLL_STEPS = 10 # максимум шагов «медленного» скролла

# Поддерживаемые расширения картинок
IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
