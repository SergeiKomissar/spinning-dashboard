import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import COLORS

def inject_custom_css():
    """Внедрение кастомных CSS стилей для корпоративной тёмной темы"""
    # Кэшируем CSS в session_state чтобы не генерировать каждый раз
    if 'css_injected' not in st.session_state:
        st.session_state.css_injected = True

    st.markdown(f"""
        <style>
        /* === ОСНОВНОЙ ФОН === */
        .stApp {{
            background: linear-gradient(180deg, {COLORS['background']} 0%, #141d2f 100%);
        }}
        
        /* Скрываем стандартный header */
        header[data-testid="stHeader"] {{
            background: transparent;
        }}
        
        /* === БОКОВАЯ ПАНЕЛЬ === */
        section[data-testid="stSidebar"] {{
            background: {COLORS['card']};
            border-right: 1px solid {COLORS['grid']};
        }}
        
        /* === КАРТОЧКИ МЕТРИК === */
        div[data-testid="stMetric"] {{
            background: {COLORS['card']};
            padding: 20px;
            border-radius: 8px;
            border: 1px solid {COLORS['grid']};
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }}
        
        div[data-testid="stMetric"] label {{
            color: {COLORS['text_secondary']} !important;
            font-size: 13px !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
            color: {COLORS['text']} !important;
            font-size: 26px !important;
            font-weight: 600 !important;
        }}
        
        /* === EXPANDER === */
        div[data-testid="stExpander"] {{
            background: {COLORS['card']};
            border: 1px solid {COLORS['grid']};
            border-radius: 8px;
        }}
        
        div[data-testid="stExpander"] summary {{
            color: {COLORS['text']} !important;
        }}
        
        /* === КНОПКИ - КОРПОРАТИВНЫЙ СТИЛЬ === */
        .stButton > button {{
            background: {COLORS['card']};
            color: {COLORS['text']};
            border: 1px solid {COLORS['grid']};
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.2s ease;
            box-shadow: none;
        }}
        
        .stButton > button:hover {{
            background: {COLORS['card_hover']};
            border-color: {COLORS['primary']};
            color: {COLORS['primary']};
            transform: none;
            box-shadow: 0 0 0 1px {COLORS['primary']};
        }}
        
        .stButton > button:active {{
            background: {COLORS['grid']};
        }}
        
        /* Кнопка выхода (secondary) */
        div[data-testid="stButton"] > button[kind="secondary"] {{
            background: transparent;
            color: {COLORS['danger']};
            border: 1px solid {COLORS['danger']};
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 500;
        }}
        
        div[data-testid="stButton"] > button[kind="secondary"]:hover {{
            background: rgba(239, 68, 68, 0.1);
            border-color: {COLORS['danger']};
            color: {COLORS['danger']};
            transform: none;
            box-shadow: none;
        }}
        
        /* === ТАБЛИЦЫ === */
        .dataframe {{
            background: {COLORS['card']} !important;
            color: {COLORS['text']} !important;
            border-radius: 8px;
            overflow: hidden;
        }}
        
        .dataframe th {{
            background: {COLORS['card_hover']} !important;
            color: {COLORS['text']} !important;
            padding: 12px !important;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
        }}
        
        .dataframe td {{
            background: {COLORS['card']} !important;
            color: {COLORS['text']} !important;
            padding: 10px !important;
            border-color: {COLORS['grid']} !important;
        }}
        
        /* === СПИННЕР === */
        .stSpinner > div {{
            border-color: {COLORS['primary']} transparent transparent transparent !important;
        }}
        
        /* === ЗАГОЛОВОК ДАШБОРДА === */
        .dashboard-header {{
            font-size: 28px;
            font-weight: 600;
            color: {COLORS['text']};
            text-align: center;
            padding: 24px 0;
            margin-bottom: 24px;
            border-bottom: 1px solid {COLORS['grid']};
            letter-spacing: -0.3px;
        }}
        
        .dashboard-header .icon {{
            margin-right: 12px;
        }}
        
        /* === ЗАГОЛОВОК ПАРТИИ === */
        .party-header {{
            font-size: 18px;
            color: {COLORS['text']};
            margin: 16px 0;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .party-badge {{
            background: {COLORS['card_hover']};
            color: {COLORS['primary']};
            padding: 6px 14px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            border: 1px solid {COLORS['grid']};
        }}
        
        /* === КАРТОЧКА === */
        .card {{
            background: {COLORS['card']};
            border-radius: 8px;
            padding: 20px;
            border: 1px solid {COLORS['grid']};
            margin-bottom: 16px;
        }}
        
        /* === СТАТУСЫ === */
        .status-good {{
            color: {COLORS['success']};
            font-size: 20px;
        }}
        
        .status-bad {{
            color: {COLORS['danger']};
            font-size: 20px;
        }}
        
        .status-warn {{
            color: {COLORS['warning']};
            font-size: 20px;
        }}
        
        /* === СКРОЛЛБАР === */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: {COLORS['background']};
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: {COLORS['grid']};
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: {COLORS['muted']};
        }}
        
        /* === ТЕКСТ === */
        p, span, div {{
            color: {COLORS['text']};
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            color: {COLORS['text']} !important;
        }}
        
        /* === ВКЛАДКИ === */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            background: {COLORS['card']};
            padding: 6px;
            border-radius: 8px;
            border: 1px solid {COLORS['grid']};
        }}
        
        .stTabs [data-baseweb="tab"] {{
            background: transparent;
            color: {COLORS['text_secondary']};
            border-radius: 6px;
            padding: 8px 16px;
        }}
        
        .stTabs [aria-selected="true"] {{
            background: {COLORS['card_hover']};
            color: {COLORS['text']} !important;
            border: 1px solid {COLORS['grid']};
        }}
        
        /* === SELECTBOX === */
        .stSelectbox [data-baseweb="select"] {{
            background: {COLORS['card']};
            border-color: {COLORS['grid']};
            border-radius: 6px;
        }}
        
        .stSelectbox [data-baseweb="select"]:hover {{
            border-color: {COLORS['primary']};
        }}
        
        /* === СЕКЦИЯ ЗАГОЛОВОК === */
        .section-header {{
            color: {COLORS['text']};
            font-size: 18px;
            font-weight: 600;
            margin: 24px 0 16px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid {COLORS['grid']};
        }}
        
        /* === INFO БЛОК === */
        .info-block {{
            background: {COLORS['card']};
            padding: 14px 16px;
            border-radius: 6px;
            margin-bottom: 16px;
            border-left: 3px solid {COLORS['primary']};
        }}
        
        .info-block h4 {{
            color: {COLORS['text']};
            margin: 0 0 6px 0;
            font-size: 15px;
            font-weight: 600;
        }}
        
        .info-block p {{
            color: {COLORS['text_secondary']};
            margin: 0;
            font-size: 13px;
            line-height: 1.5;
        }}
        </style>
    """, unsafe_allow_html=True)


def render_page_header():
    """Отрисовка заголовка страницы"""
    inject_custom_css()
    
    st.markdown(
        '<div class="dashboard-header"><span class="icon">🏭</span>Качество термообработанной нити</div>', 
        unsafe_allow_html=True
    )


def render_party_header(party_number):
    """Отрисовка заголовка партии"""
    st.markdown(f'''
        <div class="party-header">
            <span>Текущая партия</span>
            <span class="party-badge">№ {int(party_number) - 714}</span>
        </div>
    ''', unsafe_allow_html=True)


def render_metrics_section(metrics):
    """Отрисовка секции с метриками"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_color = "normal" if metrics['avg_strength'] >= 270 else "inverse"
        st.metric(
            "⚡ Средняя нагрузка",
            f"{metrics['avg_strength']} сН/текс",
            delta=f"мин: 270",
            delta_color=delta_color
        )
    
    with col2:
        delta_color = "normal" if metrics['avg_cv'] <= 9.0 else "inverse"
        st.metric(
            "📊 Коэф. вариации",
            f"{metrics['avg_cv']} %",
            delta=f"макс: 9.0",
            delta_color=delta_color
        )
        
    with col3:
        st.metric(
            "🔧 Машин в партии",
            metrics['total_machines'],
            delta="активных"
        )
    
    with col4:
        total_issues = metrics['low_strength_count'] + metrics['high_cv_count'] + metrics['bad_density_count']
        st.metric(
            "⚠️ Отклонений",
            total_issues,
            delta="требуют внимания" if total_issues > 0 else "всё в норме",
            delta_color="inverse" if total_issues > 0 else "normal"
        )
