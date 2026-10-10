import streamlit as st
import numpy as np
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import COLORS, QUALITY_THRESHOLDS_50 as QUALITY_THRESHOLDS, TWIST50_PARTY_OFFSET
from utils.auth import login_form
from components.spc import (calc_xbar_r_data, calc_p_chart_data, calc_xmr_data, detect_out_of_control,
                            create_control_chart, create_p_chart, render_spc_summary)
from components.layout import inject_custom_css, render_top_bar, render_sidebar_nav, get_session_df

st.set_page_config(
    page_title="Контрольные карты | 50 кр/м",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ============================================================
# ГЛАВНАЯ СТРАНИЦА
# ============================================================

def main():


    if not login_form():
        return

    inject_custom_css()

    st.markdown(
        '<div class="dashboard-header">Контрольные карты Шухарта — 50 кр/м</div>',
        unsafe_allow_html=True
    )

    render_sidebar_nav()
    render_top_bar(refresh_key="spc_refresh_50")

    df = get_session_df()

    if df is None or df.empty:
        st.error("Не удалось загрузить данные.")
        return

    # Фильтрация по крутке 50
    if 'Крутка' in df.columns:
        df = df[df['Крутка'] == 50].copy()

    twist50_offset = TWIST50_PARTY_OFFSET

    st.markdown("""
        <div class="info-block">
            <h4>Статистическое управление процессом (SPC) — Нить 50 кр/м</h4>
            <p>Контрольные карты построены по ГОСТ ISO 7870-2.
            Подгруппа = все машины одной партии. Красные точки — сигналы выхода из управляемого состояния.
            Жёлтые пунктирные линии — предупредительные границы (±2σ).</p>
        </div>
    """, unsafe_allow_html=True)

    settings_cols = st.columns([2, 2, 2])
    with settings_cols[0]:
        n_parties = st.selectbox(
            "Количество партий для анализа:",
            [10, 15, 20, 25, 30, 50, 100, 200, 500, 1000, "Все"], index=2, key="spc_n_parties_50"
        )

    all_parties = sorted(df['№ партии'].dropna().unique())
    if n_parties == "Все":
        selected_parties = all_parties
    else:
        selected_parties = all_parties[-n_parties:] if len(all_parties) > n_parties else all_parties
    df_filtered = df[df['№ партии'].isin(selected_parties)]

    strength_col = 'Относительная разрывная нагрузка, сН/текс'
    cv_col = 'Коэффициент вариации, %'

    # ============================================================
    # 1. X-BAR - R КАРТА ПРОЧНОСТИ
    # ============================================================
    st.markdown('<div class="section-header">X\u0304-R карта: Разрывная нагрузка</div>', unsafe_allow_html=True)

    xbar_r_data = calc_xbar_r_data(df_filtered, strength_col, offset=twist50_offset)

    if xbar_r_data:
        signals_xbar = detect_out_of_control(
            xbar_r_data['x_bars'], xbar_r_data['x_bar_bar'],
            xbar_r_data['x_ucl'], xbar_r_data['x_lcl']
        )
        render_spc_summary(xbar_r_data, signals_xbar, "Среднее прочности (X\u0304)")

        fig_xbar = create_control_chart(
            xbar_r_data['party_labels'], xbar_r_data['x_bars'],
            xbar_r_data['x_bar_bar'], xbar_r_data['x_ucl'], xbar_r_data['x_lcl'],
            title='X\u0304-карта: Средняя разрывная нагрузка по партии',
            y_title='Средняя нагрузка, сН/текс',
            signals=signals_xbar,
            spec_limit=QUALITY_THRESHOLDS['strength_min'],
            spec_label=f"Мин. допуск: {QUALITY_THRESHOLDS['strength_min']}",
            sigma=xbar_r_data['sigma_x']
        )
        st.plotly_chart(fig_xbar, width='stretch', config={'displayModeBar': False})

        signals_r = detect_out_of_control(
            xbar_r_data['ranges'], xbar_r_data['r_bar'],
            xbar_r_data['r_ucl'], xbar_r_data['r_lcl']
        )
        render_spc_summary({'x_bars': xbar_r_data['ranges']}, signals_r, "Размах (R)")

        fig_r = create_control_chart(
            xbar_r_data['party_labels'], xbar_r_data['ranges'],
            xbar_r_data['r_bar'], xbar_r_data['r_ucl'], xbar_r_data['r_lcl'],
            title='R-карта: Размах разрывной нагрузки в партии',
            y_title='Размах, сН/текс', signals=signals_r, zone_lines=False
        )
        st.plotly_chart(fig_r, width='stretch', config={'displayModeBar': False})

        with st.expander("Параметры расчёта X\u0304-R карты"):
            param_cols = st.columns(4)
            with param_cols[0]:
                st.markdown(f"**Средний размер подгруппы (n):** {xbar_r_data['avg_n']}")
                st.markdown(f"**Число подгрупп (k):** {len(xbar_r_data['x_bars'])}")
            with param_cols[1]:
                st.markdown(f"**X\u0304\u0304 (grand mean):** {xbar_r_data['x_bar_bar']:.2f}")
                st.markdown(f"**R\u0304 (mean range):** {xbar_r_data['r_bar']:.2f}")
            with param_cols[2]:
                st.markdown(f"**A2:** {xbar_r_data['A2']}")
                st.markdown(f"**D3:** {xbar_r_data['D3']}")
                st.markdown(f"**D4:** {xbar_r_data['D4']}")
            with param_cols[3]:
                st.markdown(f"**UCL (X\u0304):** {xbar_r_data['x_ucl']:.2f}")
                st.markdown(f"**LCL (X\u0304):** {xbar_r_data['x_lcl']:.2f}")
                st.markdown(f"**UCL (R):** {xbar_r_data['r_ucl']:.2f}")
    else:
        st.warning("Недостаточно данных для построения X\u0304-R карты")

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ============================================================
    # 2. X-BAR - S КАРТА CV
    # ============================================================
    st.markdown('<div class="section-header">X\u0304-S карта: Коэффициент вариации</div>', unsafe_allow_html=True)

    xbar_s_data = calc_xbar_r_data(df_filtered, cv_col, offset=twist50_offset)

    if xbar_s_data:
        signals_xbar_cv = detect_out_of_control(
            xbar_s_data['x_bars'], xbar_s_data['x_bar_bar'],
            xbar_s_data['x_ucl'], xbar_s_data['x_lcl']
        )
        render_spc_summary(xbar_s_data, signals_xbar_cv, "Среднее CV (X\u0304)")

        fig_xbar_cv = create_control_chart(
            xbar_s_data['party_labels'], xbar_s_data['x_bars'],
            xbar_s_data['x_bar_bar'], xbar_s_data['x_ucl'], xbar_s_data['x_lcl'],
            title='X\u0304-карта: Средний CV по партии',
            y_title='Средний CV, %', signals=signals_xbar_cv,
            spec_limit=QUALITY_THRESHOLDS['cv_max'],
            spec_label=f"Макс. допуск: {QUALITY_THRESHOLDS['cv_max']}%",
            sigma=xbar_s_data['sigma_x']
        )
        st.plotly_chart(fig_xbar_cv, width='stretch', config={'displayModeBar': False})

        signals_s = detect_out_of_control(
            xbar_s_data['stds'], xbar_s_data['s_bar'],
            xbar_s_data['s_ucl'], xbar_s_data['s_lcl']
        )
        render_spc_summary({'x_bars': xbar_s_data['stds']}, signals_s, "Стандартное отклонение CV (S)")

        fig_s = create_control_chart(
            xbar_s_data['party_labels'], xbar_s_data['stds'],
            xbar_s_data['s_bar'], xbar_s_data['s_ucl'], xbar_s_data['s_lcl'],
            title='S-карта: Стандартное отклонение CV в партии',
            y_title='Стд. отклонение CV, %', signals=signals_s, zone_lines=False
        )
        st.plotly_chart(fig_s, width='stretch', config={'displayModeBar': False})

        with st.expander("Параметры расчёта X\u0304-S карты"):
            param_cols = st.columns(4)
            with param_cols[0]:
                st.markdown(f"**Средний размер подгруппы (n):** {xbar_s_data['avg_n']}")
            with param_cols[1]:
                st.markdown(f"**X\u0304\u0304:** {xbar_s_data['x_bar_bar']:.2f}%")
                st.markdown(f"**S\u0304:** {xbar_s_data['s_bar']:.2f}")
            with param_cols[2]:
                st.markdown(f"**B3:** {xbar_s_data['B3']}")
                st.markdown(f"**B4:** {xbar_s_data['B4']}")
            with param_cols[3]:
                st.markdown(f"**UCL (S):** {xbar_s_data['s_ucl']:.2f}")
                st.markdown(f"**LCL (S):** {xbar_s_data['s_lcl']:.2f}")
    else:
        st.warning("Недостаточно данных для построения X\u0304-S карты")

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # Пропуск тяжёлых графиков при большом объёме данных
    _n = len(all_parties) if n_parties == "Все" else n_parties
    if _n > 200:
        st.info("p-карты и X-MR карта не отображаются при выборе более 200 партий (долгие вычисления).")
        return

    # ============================================================
    # 3. P-КАРТА
    # ============================================================
    st.markdown('<div class="section-header">p-карта: Доля несоответствующих машин</div>', unsafe_allow_html=True)

    p_chart_col1, p_chart_col2 = st.columns(2)

    with p_chart_col1:
        p_data_strength = calc_p_chart_data(
            df_filtered, strength_col,
            threshold=QUALITY_THRESHOLDS['strength_min'], mode='less',
            offset=twist50_offset
        )
        if p_data_strength:
            fig_p_str, sig_p_str = create_p_chart(
                p_data_strength,
                f'p-карта: прочность < {QUALITY_THRESHOLDS["strength_min"]}'
            )
            render_spc_summary(p_data_strength, sig_p_str, "Доля слабых")
            st.plotly_chart(fig_p_str, width='stretch', config={'displayModeBar': False})

    with p_chart_col2:
        p_data_cv = calc_p_chart_data(
            df_filtered, cv_col,
            threshold=QUALITY_THRESHOLDS['cv_max'], mode='greater',
            offset=twist50_offset
        )
        if p_data_cv:
            fig_p_cv, sig_p_cv = create_p_chart(
                p_data_cv,
                f'p-карта: CV > {QUALITY_THRESHOLDS["cv_max"]}%'
            )
            render_spc_summary(p_data_cv, sig_p_cv, "Доля нестабильных")
            st.plotly_chart(fig_p_cv, width='stretch', config={'displayModeBar': False})

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # ============================================================
    # 4. X-MR КАРТА ПО ОТДЕЛЬНОЙ МАШИНЕ
    # ============================================================
    st.markdown('<div class="section-header">X-MR карта: Мониторинг отдельной машины</div>', unsafe_allow_html=True)

    st.markdown("""
        <div class="info-block">
            <h4>Индивидуальная контрольная карта</h4>
            <p>Выберите машину для отслеживания её разрывной нагрузки от партии к партии.
            X-карта показывает индивидуальные значения, MR-карта — скользящие размахи между соседними партиями.</p>
        </div>
    """, unsafe_allow_html=True)

    machines = sorted(df_filtered['№ ПМ'].dropna().unique())
    machine_cols = st.columns([2, 2, 2])

    with machine_cols[0]:
        selected_machine = st.selectbox(
            "Выберите машину:", machines,
            format_func=lambda x: f"ПМ {int(x)}", key="spc_machine_50"
        )

    with machine_cols[1]:
        xmr_metric = st.selectbox(
            "Метрика:", [strength_col, cv_col],
            format_func=lambda x: "Разрывная нагрузка" if "нагрузка" in x else "Коэф. вариации",
            key="spc_xmr_metric_50"
        )

    if selected_machine:
        xmr_data = calc_xmr_data(df_filtered, selected_machine, xmr_metric, offset=twist50_offset)

        if xmr_data:
            signals_xmr = detect_out_of_control(
                xmr_data['values'], xmr_data['x_bar'],
                xmr_data['x_ucl'], xmr_data['x_lcl']
            )
            metric_label = "Прочность" if "нагрузка" in xmr_metric else "CV"
            render_spc_summary({'x_bars': xmr_data['values']}, signals_xmr, f"ПМ {int(selected_machine)} — {metric_label}")

            xmr_cols = st.columns(2)

            with xmr_cols[0]:
                spec = QUALITY_THRESHOLDS['strength_min'] if "нагрузка" in xmr_metric else QUALITY_THRESHOLDS['cv_max']
                spec_lbl = f"Мин: {spec}" if "нагрузка" in xmr_metric else f"Макс: {spec}"
                fig_x = create_control_chart(
                    xmr_data['party_labels'], xmr_data['values'],
                    xmr_data['x_bar'], xmr_data['x_ucl'], xmr_data['x_lcl'],
                    title=f'X-карта: ПМ {int(selected_machine)}',
                    y_title=xmr_metric.split(',')[0], signals=signals_xmr,
                    spec_limit=spec, spec_label=spec_lbl, sigma=xmr_data['sigma_est']
                )
                st.plotly_chart(fig_x, width='stretch', config={'displayModeBar': False})

            with xmr_cols[1]:
                signals_mr = detect_out_of_control(
                    xmr_data['mr'], xmr_data['mr_bar'],
                    xmr_data['mr_ucl'], xmr_data['mr_lcl']
                )
                fig_mr = create_control_chart(
                    xmr_data['mr_parties'], xmr_data['mr'],
                    xmr_data['mr_bar'], xmr_data['mr_ucl'], xmr_data['mr_lcl'],
                    title=f'MR-карта: ПМ {int(selected_machine)}',
                    y_title='Скользящий размах', signals=signals_mr, zone_lines=False
                )
                st.plotly_chart(fig_mr, width='stretch', config={'displayModeBar': False})

            with st.expander(f"Параметры X-MR карты для ПМ {int(selected_machine)}"):
                param_cols = st.columns(3)
                with param_cols[0]:
                    st.markdown(f"**Точек:** {len(xmr_data['values'])}")
                    st.markdown(f"**X\u0304:** {xmr_data['x_bar']:.2f}")
                with param_cols[1]:
                    st.markdown(f"**MR\u0304:** {xmr_data['mr_bar']:.2f}")
                    st.markdown(f"**sigma (MR\u0304/d2):** {xmr_data['sigma_est']:.2f}")
                with param_cols[2]:
                    st.markdown(f"**UCL (X):** {xmr_data['x_ucl']:.2f}")
                    st.markdown(f"**LCL (X):** {xmr_data['x_lcl']:.2f}")
                    st.markdown(f"**UCL (MR):** {xmr_data['mr_ucl']:.2f}")
        else:
            st.warning(f"Недостаточно данных для машины ПМ {int(selected_machine)}")

    # ============================================================
    # 5. X-MR КАРТА АППАРАТА ВТВ (отклонение от среднего партии)
    # ============================================================
    st.markdown('<div class="section-header">X-MR карта: Аппарат ВТВ</div>', unsafe_allow_html=True)

    st.markdown("""
        <div class="info-block">
            <h4>Контроль термообработки</h4>
            <p>Точка — среднее отклонение прочности от среднего партии для бобин,
            прошедших через выбранный аппарат. CL около нуля — аппарат работает как остальные;
            устойчивый уход вниз или выход за границы — разладка термообработки.</p>
        </div>
    """, unsafe_allow_html=True)

    if '№ ВТВ' in df_filtered.columns:
        df_vtv = df_filtered.copy()
        df_vtv['ВТВ'] = pd.to_numeric(df_vtv['№ ВТВ'], errors='coerce')
        df_vtv = df_vtv[df_vtv['ВТВ'].between(1, 19)]
        df_vtv['Отклонение'] = df_vtv[strength_col] - df_vtv.groupby('№ партии')[strength_col].transform('mean')

        vtv_nums = sorted(df_vtv['ВТВ'].dropna().unique())
        if vtv_nums:
            vtv_cols = st.columns([2, 2, 2])
            with vtv_cols[0]:
                selected_vtv_spc = st.selectbox(
                    "Выберите аппарат:", vtv_nums,
                    format_func=lambda x: f"ВТВ №{int(x)}", key="spc_vtv_50"
                )

            sub = df_vtv[df_vtv['ВТВ'] == selected_vtv_spc]
            by_party = sub.groupby('№ партии')['Отклонение'].agg(['mean', 'count']).reset_index()
            by_party = by_party[by_party['count'] >= 2].sort_values('№ партии')

            if len(by_party) >= 5:
                values = by_party['mean'].round(2).values
                party_labels = [int(p) - twist50_offset for p in by_party['№ партии']]

                mr = np.abs(np.diff(values))
                mr_bar = mr.mean()
                sigma_est = mr_bar / 1.128
                x_bar = values.mean()
                x_ucl = x_bar + 2.66 * mr_bar
                x_lcl = x_bar - 2.66 * mr_bar
                mr_ucl = 3.267 * mr_bar

                signals_vtv = detect_out_of_control(values, x_bar, x_ucl, x_lcl)
                render_spc_summary({'x_bars': values}, signals_vtv, f"ВТВ №{int(selected_vtv_spc)} — отклонение прочности")

                vtv_chart_cols = st.columns(2)
                with vtv_chart_cols[0]:
                    fig_vx = create_control_chart(
                        party_labels, list(values),
                        x_bar, x_ucl, x_lcl,
                        title=f'X-карта: ВТВ №{int(selected_vtv_spc)}',
                        y_title='Отклонение, сН/текс', signals=signals_vtv,
                        sigma=sigma_est
                    )
                    fig_vx.add_hline(y=0, line=dict(color=COLORS['text_secondary'], width=1, dash='dot'))
                    st.plotly_chart(fig_vx, width='stretch', config={'displayModeBar': False}, key='spc_vtv_x')

                with vtv_chart_cols[1]:
                    signals_vmr = detect_out_of_control(list(mr), mr_bar, mr_ucl, 0)
                    fig_vmr = create_control_chart(
                        party_labels[1:], list(mr),
                        mr_bar, mr_ucl, 0,
                        title=f'MR-карта: ВТВ №{int(selected_vtv_spc)}',
                        y_title='Скользящий размах', signals=signals_vmr, zone_lines=False
                    )
                    st.plotly_chart(fig_vmr, width='stretch', config={'displayModeBar': False}, key='spc_vtv_mr')

                with st.expander(f"Параметры карты для ВТВ №{int(selected_vtv_spc)}"):
                    p_cols = st.columns(3)
                    with p_cols[0]:
                        st.markdown(f"**Точек (партий):** {len(values)}")
                        st.markdown(f"**X\u0304:** {x_bar:+.2f}")
                    with p_cols[1]:
                        st.markdown(f"**MR\u0304:** {mr_bar:.2f}")
                        st.markdown(f"**sigma (MR\u0304/d2):** {sigma_est:.2f}")
                    with p_cols[2]:
                        st.markdown(f"**UCL (X):** {x_ucl:+.2f}")
                        st.markdown(f"**LCL (X):** {x_lcl:+.2f}")
            else:
                st.warning(f"Недостаточно партий для ВТВ №{int(selected_vtv_spc)} (нужно минимум 5)")
        else:
            st.info("Нет данных с номерами аппаратов ВТВ за выбранный период")
    else:
        st.info("В таблице нет колонки '№ ВТВ'")

    st.markdown(f"""
        <div style="text-align: center; margin-top: 40px; padding: 20px; color: {COLORS['text_secondary']};">
            <small>Контрольные карты по ГОСТ ISO 7870-2 | Нить 50 кр/м | Данные из Google Sheets</small>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()