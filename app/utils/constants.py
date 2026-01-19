# Тёмная цветовая схема (современный промышленный стиль)
COLORS = {
    'primary': '#00D4FF',       # Яркий голубой (акцент)
    'secondary': '#8B5CF6',     # Фиолетовый
    'success': '#10B981',       # Изумрудный зелёный
    'warning': '#F59E0B',       # Янтарный
    'danger': '#EF4444',        # Красный
    'text': '#F1F5F9',          # Светло-серый для текста
    'text_secondary': '#94A3B8', # Приглушённый текст
    'background': '#0F172A',    # Тёмно-синий фон
    'card': '#1E293B',          # Фон карточек
    'card_hover': '#334155',    # Фон карточек при наведении
    'grid': '#334155',          # Сетка графиков
    'accent': '#06B6D4',        # Бирюзовый акцент
    'muted': '#64748B',         # Приглушённый серый
    'gradient_start': '#0F172A',
    'gradient_end': '#1E293B',
}

# Настройки графиков
CHART_CONFIG = {
    'font_family': "'Inter', 'Segoe UI', sans-serif",
    'title_size': 24,
    'axis_title_size': 14,
    'label_size': 12,
}

# Пороговые значения качества
QUALITY_THRESHOLDS = {
    'strength_min': 270,
    'cv_max': 9.0,
    'density_range': (28.3, 29.5)
}

# Идентификатор таблицы по умолчанию
DEFAULT_SHEET_ID = '1S1obWIvuasnedJrKNeOQvJuoT-vrZ7v6EgivXiYsotc'

# Настройки gauge-индикаторов
GAUGE_CONFIG = {
    'strength': {
        'min': 200,
        'max': 350,
        'threshold': 270,
        'title': 'Разрывная нагрузка',
        'unit': 'сН/текс'
    },
    'cv': {
        'min': 0,
        'max': 15,
        'threshold': 9.0,
        'title': 'Коэф. вариации',
        'unit': '%',
        'inverse': True  # Меньше = лучше
    },
    'density': {
        'min': 27,
        'max': 31,
        'range': (28.3, 29.5),
        'title': 'Лин. плотность',
        'unit': 'текс'
    }
}
