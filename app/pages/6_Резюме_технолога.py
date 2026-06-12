import streamlit as st
import json
import sys
import os
from datetime import datetime

st.set_page_config(
    page_title="Резюме технолога | Нить 50 кр/м",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.layout import inject_custom_css
from utils.data_processing import load_data
from utils.constants import QUALITY_THRESHOLDS_50 as QUALITY_THRESHOLDS, COLORS
from utils.auth import login_form, logout_button, is_admin
from utils import ai_summary


def main():
    if not login_form():
        return

    inject_custom_css()

    st.markdown(
        '<div class="dashboard-header">Резюме технолога — 50 кр/м</div>',
        unsafe_allow_html=True
    )

    header_cols = st.columns([3, 2, 1, 1])
    with header_cols[0]:
        st.markdown(f"<span style='color:#94a3b8;font-size:13px;'>Пользователь: <b>{st.session_state.user_info['name']}</b></span>", unsafe_allow_html=True)
    with header_cols[1]:
        st.markdown(f"<span style='color:#64748b;font-size:12px;'>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</span>", unsafe_allow_html=True)
    with header_cols[2]:
        if st.button('Обновить', key="ai_refresh"):
            load_data.clear()
            st.rerun()
    with header_cols[3]:
        logout_button()

    # --- Кастомная навигация ---
    st.markdown("""<style>[data-testid="stSidebarNav"] {display: none;}</style>""", unsafe_allow_html=True)
    st.sidebar.markdown("### Дашборд")
    st.sidebar.page_link("pages/1_Дашборд_нити_с_круткой_50_крм.py", label="Нить с круткой 50 кр/м", icon="🧵")
    st.sidebar.markdown("### Аналитика")
    st.sidebar.page_link("pages/6_Резюме_технолога.py", label="Резюме технолога", icon="🤖")
    st.sidebar.page_link("pages/8_Паспорт_машин.py", label="Паспорт машин", icon="🩺")
    st.sidebar.markdown("### Контрольные карты")
    st.sidebar.page_link("pages/3_Контрольные_карты_50_крм.py", label="Контрольные карты 50 кр/м", icon="📈")
    st.sidebar.markdown("### Термообработка")
    st.sidebar.page_link("pages/4_Анализ_аппаратов_ВТВ.py", label="Анализ аппаратов ВТВ", icon="🔥")
    st.sidebar.markdown("### Архив")
    st.sidebar.page_link("pages/7_Архив_Дашборд_100_крм.py", label="Дашборд нити 100 кр/м", icon="🗄️")
    st.sidebar.page_link("pages/2_Контрольные_карты_100_крм.py", label="Контрольные карты 100 кр/м", icon="🗄️")
    st.sidebar.markdown("### Администратор")
    st.sidebar.page_link("pages/5_Статистика_для_администратора.py", label="Статистика посещений", icon="👤")

    with st.spinner('Загрузка данных...'):
        if 'df' not in st.session_state:
            st.session_state.df = load_data()
        df = st.session_state.df.copy() if st.session_state.df is not None else None

    if df is None or df.empty:
        st.error("Не удалось загрузить данные.")
        return

    if 'Крутка' in df.columns:
        df = df[df['Крутка'] == 50].copy()
    if df['№ партии'].dropna().empty:
        st.warning("Нет данных по крутке 50")
        return

    twist50_offset = 845

    st.markdown("""
        <div class="info-block">
            <h4>Автоматическая технологическая сводка</h4>
            <p>Статистика считается детерминированно (правила Нельсона, отклонения машин и аппаратов,
            Cpk, динамика брака), затем нейросеть превращает факты в краткую сводку с приоритетами.
            Сводка генерируется один раз на партию и кэшируется — повторные просмотры бесплатны.</p>
        </div>
    """, unsafe_allow_html=True)

    # --- Диагностика (всегда, бесплатно) ---
    try:
        facts = ai_summary.build_facts(df, QUALITY_THRESHOLDS, twist50_offset)
    except Exception as e:
        st.error(f"Ошибка диагностики: {e}")
        return

    party_disp = facts['партия']
    fhash = ai_summary.facts_hash(facts)
    api_key = ai_summary.get_api_key()

    # --- Выбор модели (тестовый режим) ---
    model_ids = list(ai_summary.MODELS.keys())
    sel_cols = st.columns([3, 2, 2])
    with sel_cols[0]:
        model = st.selectbox(
            "Модель (тестовый режим — сравните качество):", model_ids,
            format_func=lambda m: ai_summary.MODELS[m]['label'],
            index=model_ids.index(ai_summary.DEFAULT_MODEL), key="ai_model"
        )

    if not api_key:
        st.warning(
            "Ключ OpenRouter не настроен — показана детерминированная сводка без нейросети. "
            "Добавьте OPENROUTER_API_KEY в Secrets приложения (Streamlit Cloud → App settings → Secrets):\n\n"
            '`OPENROUTER_API_KEY = "sk-or-v1-..."`'
        )
        st.markdown(f'<div class="section-header">Сводка по партии №{party_disp}</div>', unsafe_allow_html=True)
        st.markdown(ai_summary.render_fallback(facts))
    else:
        cached = ai_summary.get_cached(party_disp, model, fhash)

        regen_cols = st.columns([2, 4])
        with regen_cols[0]:
            force = st.button("Сгенерировать заново", key="ai_force")

        if cached and not force:
            summary, in_t, out_t, cost, created = cached
            st.markdown(f'<div class="section-header">Сводка по партии №{party_disp}</div>', unsafe_allow_html=True)
            st.markdown(summary)
            st.markdown(
                f"<span style='color:{COLORS['text_secondary']};font-size:12px;'>"
                f"Сгенерировано {created} | {ai_summary.MODELS[model]['label']} | "
                f"токены: {in_t}+{out_t} | стоимость: ${cost:.4f} | из кэша</span>",
                unsafe_allow_html=True)
        else:
            with st.spinner('Нейросеть анализирует партию...'):
                try:
                    summary, in_t, out_t, cost = ai_summary.generate(facts, model)
                    ai_summary.save_summary(party_disp, model, fhash, summary, in_t, out_t, cost)
                    st.markdown(f'<div class="section-header">Сводка по партии №{party_disp}</div>', unsafe_allow_html=True)
                    st.markdown(summary)
                    st.markdown(
                        f"<span style='color:{COLORS['text_secondary']};font-size:12px;'>"
                        f"Сгенерировано только что | {ai_summary.MODELS[model]['label']} | "
                        f"токены: {in_t}+{out_t} | стоимость: ${cost:.4f}</span>",
                        unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Ошибка генерации ({e}). Показана сводка без нейросети.")
                    st.markdown(f'<div class="section-header">Сводка по партии №{party_disp}</div>', unsafe_allow_html=True)
                    st.markdown(ai_summary.render_fallback(facts))

        spent, n_gen = ai_summary.total_spend()
        st.markdown(
            f"<span style='color:{COLORS['text_secondary']};font-size:12px;'>"
            f"Всего сгенерировано сводок: {n_gen} | суммарно потрачено: ${spent:.3f}</span>",
            unsafe_allow_html=True)

    # --- Тестовый режим: что видит нейросеть ---
    if is_admin():
        with st.expander("Факты диагностики (что передаётся нейросети)"):
            st.code(json.dumps(facts, ensure_ascii=False, indent=2, default=str), language='json')
        with st.expander("Справочник производства (что подгружается к фактам)"):
            from utils import domain_knowledge
            st.markdown(
                f"<span style='color:{COLORS['text_secondary']};font-size:13px;'>"
                "Справочник редактируется в Google Таблице «СтатПряд2025», лист <b>«Справочник»</b> — "
                "правьте текст в колонке C, изменения подхватываются в течение 10 минут. "
                "Пустая ячейка отключает блок. Колонку A (ключи) не менять.</span>",
                unsafe_allow_html=True)
            st.code(domain_knowledge.select_knowledge(facts))

    st.markdown(f"""
        <div style="text-align: center; margin-top: 40px; padding: 20px; color: {COLORS['text_secondary']};">
            <small>Резюме технолога | Нить 50 кр/м | Диагностика: правила Нельсона, Cpk, анализ ПМ и ВТВ</small>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
