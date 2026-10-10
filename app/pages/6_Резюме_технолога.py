import streamlit as st
import json
import sys
import os

st.set_page_config(
    page_title="Резюме технолога | Нить 50 кр/м",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.layout import inject_custom_css, render_top_bar, render_sidebar_nav, get_session_df
from utils.constants import QUALITY_THRESHOLDS_50 as QUALITY_THRESHOLDS, COLORS, TWIST50_PARTY_OFFSET
from utils.auth import login_form, is_admin
from utils import ai_summary


def main():
    if not login_form():
        return

    inject_custom_css()

    st.markdown(
        '<div class="dashboard-header">Резюме технолога — 50 кр/м</div>',
        unsafe_allow_html=True
    )

    render_top_bar(refresh_key="ai_refresh")

    render_sidebar_nav()

    df = get_session_df()

    if df is None or df.empty:
        st.error("Не удалось загрузить данные.")
        return

    if 'Крутка' in df.columns:
        df = df[df['Крутка'] == 50].copy()
    if df['№ партии'].dropna().empty:
        st.warning("Нет данных по крутке 50")
        return

    twist50_offset = TWIST50_PARTY_OFFSET

    st.markdown("""
        <div class="info-block">
            <h4>Автоматическая технологическая сводка</h4>
            <p>Статистика считается детерминированно (правила Нельсона, отклонения машин и аппаратов,
            Cpk, динамика брака), затем ИИ превращает факты в краткую сводку с приоритетами.
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

    model = ai_summary.DEFAULT_MODEL

    if not api_key:
        st.warning(
            "Ключ OpenRouter не настроен — показана сводка без анализа ИИ. "
            "Добавьте OPENROUTER_API_KEY в Secrets приложения (Streamlit Cloud → App settings → Secrets):\n\n"
            '`OPENROUTER_API_KEY = "sk-or-v1-..."`'
        )
        st.markdown(f'<div class="section-header">Сводка по партии №{party_disp}</div>', unsafe_allow_html=True)
        st.markdown(ai_summary.render_fallback(facts))
    else:
        cached = ai_summary.get_cached(party_disp, model, fhash)

        # Кнопка через callback: клик ставит флаг в session_state и не теряется,
        # даже если страница в этот момент перезапускалась
        def _request_regen():
            st.session_state['ai_force_flag'] = True

        regen_cols = st.columns([2, 4])
        with regen_cols[0]:
            st.button("Сгенерировать заново", key="ai_force_btn", on_click=_request_regen)
        force = st.session_state.get('ai_force_flag', False)

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
            with st.spinner('ИИ анализирует партию...'):
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
                    st.error(f"Ошибка генерации ({e}). Показана сводка без анализа ИИ.")
                    st.markdown(f'<div class="section-header">Сводка по партии №{party_disp}</div>', unsafe_allow_html=True)
                    st.markdown(ai_summary.render_fallback(facts))
            st.session_state['ai_force_flag'] = False

        spent, n_gen = ai_summary.total_spend()
        st.markdown(
            f"<span style='color:{COLORS['text_secondary']};font-size:12px;'>"
            f"Всего сгенерировано сводок: {n_gen} | суммарно потрачено: ${spent:.3f}</span>",
            unsafe_allow_html=True)

    # --- Для администратора: что видит ИИ ---
    if is_admin():
        with st.expander("Факты диагностики (что передаётся ИИ)"):
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
