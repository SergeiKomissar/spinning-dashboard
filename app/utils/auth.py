import streamlit as st
import yaml
import sqlite3
from datetime import datetime
from pathlib import Path

# Путь к конфигурации
CONFIG_PATH = Path(__file__).parent.parent.parent / 'config' / 'users.yaml'
DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'visits.db'


def load_users():
    """Загрузка пользователей из YAML"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


def verify_password(username, password):
    """Проверка пароля"""
    config = load_users()
    if config and username in config['credentials']['usernames']:
        stored_password = str(config['credentials']['usernames'][username]['password'])
        return str(password) == stored_password
    return False


def get_user_info(username):
    """Получение информации о пользователе"""
    config = load_users()
    if config and username in config['credentials']['usernames']:
        return config['credentials']['usernames'][username]
    return None


def init_db():
    """Инициализация базы данных для логов"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            name TEXT,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            logout_time TIMESTAMP,
            duration_minutes INTEGER,
            ip_address TEXT,
            user_agent TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS page_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            page TEXT,
            view_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def log_login(username, name):
    """Логирование входа"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO visits (username, name, login_time)
        VALUES (?, ?, ?)
    ''', (username, name, datetime.now()))
    
    visit_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return visit_id


def log_logout(visit_id):
    """Логирование выхода"""
    if not visit_id:
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем время входа
    cursor.execute('SELECT login_time FROM visits WHERE id = ?', (visit_id,))
    result = cursor.fetchone()
    
    if result:
        login_time = datetime.fromisoformat(result[0])
        logout_time = datetime.now()
        duration = int((logout_time - login_time).total_seconds() / 60)
        
        cursor.execute('''
            UPDATE visits 
            SET logout_time = ?, duration_minutes = ?
            WHERE id = ?
        ''', (logout_time, duration, visit_id))
    
    conn.commit()
    conn.close()


def get_visit_stats():
    """Получение статистики посещений"""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Все посещения
    cursor.execute('''
        SELECT username, name, login_time, logout_time, duration_minutes
        FROM visits
        ORDER BY login_time DESC
        LIMIT 100
    ''')
    visits = cursor.fetchall()
    
    # Статистика по пользователям
    cursor.execute('''
        SELECT username, name, 
               COUNT(*) as visit_count,
               SUM(duration_minutes) as total_minutes,
               MAX(login_time) as last_visit
        FROM visits
        GROUP BY username
        ORDER BY visit_count DESC
    ''')
    user_stats = cursor.fetchall()
    
    # Активные сессии (без logout)
    cursor.execute('''
        SELECT username, name, login_time
        FROM visits
        WHERE logout_time IS NULL
        AND login_time > datetime('now', '-24 hours')
    ''')
    active_sessions = cursor.fetchall()
    
    conn.close()
    
    return {
        'visits': visits,
        'user_stats': user_stats,
        'active_sessions': active_sessions
    }


def login_form():
    """Форма входа"""
    
    # Инициализация состояния
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'visit_id' not in st.session_state:
        st.session_state.visit_id = None
    
    # Если уже авторизован
    if st.session_state.authenticated:
        return True
    
    # Форма входа
    st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            background: linear-gradient(145deg, #1E293B 0%, #334155 100%);
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🏭 Дашборд прядильного цеха")
        st.markdown("---")
        
        username = st.text_input("Логин", placeholder="Введите логин")
        password = st.text_input("Пароль", type="password", placeholder="Введите пароль")
        
        if st.button("Войти", width='stretch'):
            if verify_password(username, password):
                user_info = get_user_info(username)
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.user_info = user_info
                st.session_state.visit_id = log_login(username, user_info['name'])
                st.rerun()
            else:
                st.error("❌ Неверный логин или пароль")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Обратитесь к администратору для получения доступа")
    
    return False


def logout_button():
    """Кнопка выхода"""
    if st.session_state.get('authenticated'):
        if st.button("Выход", type="secondary", key="logout_btn"):
            log_logout(st.session_state.get('visit_id'))
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.user_info = None
            st.session_state.visit_id = None
            st.rerun()


def is_admin():
    """Проверка прав администратора"""
    if st.session_state.get('user_info'):
        return st.session_state.user_info.get('role') == 'admin'
    return False
