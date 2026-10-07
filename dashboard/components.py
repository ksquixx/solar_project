# dashboard/components.py
"""UI-компоненты дашборда."""
import streamlit as st
import pandas as pd

from dashboard.mock_data import (
    PANEL_ROWS, PANEL_COLS, N_PANELS, PANEL_PEAK_KW,
)


def render_station_grid(per_panel_kwh: list[float], selected_panel: int | None):
    """
    Рисует сетку панелей станции. Каждая панель — кликабельная.
    Клик устанавливает st.session_state['selected_panel'].

    :param per_panel_kwh: список выработки по панелям за день
    :param selected_panel: индекс текущей выбранной панели или None
    """
    cols = st.columns(PANEL_COLS)
    for i in range(N_PANELS):
        row = i // PANEL_COLS
        col = i % PANEL_COLS
        with cols[col]:
            is_selected = (selected_panel == i)
            css_class = "solar-panel selected" if is_selected else "solar-panel"
            value = per_panel_kwh[i] if i < len(per_panel_kwh) else 0.0

            st.markdown(
                f"""
                <div class="{css_class}">
                    <div class="panel-label">Панель {i + 1}</div>
                    <div class="panel-value">{value:.2f} кВт·ч</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Невидимая кнопка поверх — для реакции на клик
            if st.button(
                f" ",
                key=f"btn_panel_{i}",
                help=f"Выбрать панель {i + 1}",
                use_container_width=True,
            ):
                # toggle: если уже выбрана — снять выделение
                if selected_panel == i:
                    st.session_state["selected_panel"] = None
                else:
                    st.session_state["selected_panel"] = i
                st.rerun()


def render_summary(total_kwh: float, peak_kw: float,
                   per_panel_kwh: list[float], selected_panel: int | None):
    """
    Карточка итога: общая или по выбранной панели.
    """
    if selected_panel is None:
        title = "Итог по всей электростанции"
        value = total_kwh
        subtitle = f"Пиковая мощность: {peak_kw:.2f} кВт"
    else:
        title = f"Итог по панели {selected_panel + 1}"
        value = per_panel_kwh[selected_panel] if selected_panel < len(per_panel_kwh) else 0.0
        peak_panel = PANEL_PEAK_KW  # пик одной панели
        subtitle = f"Пиковая мощность панели: {peak_panel:.2f} кВт"

    st.markdown(
        f"""
        <div class="summary-card">
            <div class="summary-label">{title}</div>
            <div>
                <span class="summary-value">{value:.2f}</span>
                <span class="summary-unit">кВт·ч за сутки</span>
            </div>
            <div style="margin-top: 8px; opacity: 0.75; font-size: 0.9rem;">
                {subtitle}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_weather(weather_row: pd.Series | None):
    """
    Карточка погоды за выбранный день.
    :param weather_row: строка из weather_35135_daily.csv или None.
    """
    st.markdown("### 🌤 Погода за выбранный день")
    if weather_row is None:
        st.info("Нет данных о погоде за этот день.")
        return

    def fmt(v, unit="", digits=1):
        if pd.isna(v):
            return "—"
        return f"{v:.{digits}f}{unit}"

    items = [
        ("🌡 Средняя температура", fmt(weather_row.get("T_mean"), " °C")),
        ("🔺 Максимум",            fmt(weather_row.get("T_max"), " °C")),
        ("🔻 Минимум",             fmt(weather_row.get("T_min"), " °C")),
        ("💧 Влажность",           fmt(weather_row.get("f_mean"), " %", 0)),
        ("💨 Ветер средний",       fmt(weather_row.get("wind_speed_mean"), " м/с")),
        ("💨 Ветер макс",          fmt(weather_row.get("wind_speed_max"), " м/с")),
        ("📊 Давление среднее",    fmt(weather_row.get("P_mean"), " гПа")),
        ("📈 Тренд давления",      fmt(weather_row.get("P_change"), " гПа")),
        ("🌡 Точка росы",          fmt(weather_row.get("Td_mean"), " °C")),
    ]

    st.markdown('<div class="summary-card">', unsafe_allow_html=True)
    for label, value in items:
        st.markdown(
            f'<div class="weather-item"><span>{label}</span>'
            f'<span style="color:#ffcc00;font-weight:600;">{value}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_generation_chart(df_gen: pd.DataFrame, selected_panel: int | None,
                            per_panel_series: pd.DataFrame | None = None):
    """
    График выработки за сутки с 3-часовым шагом.
    Если выбрана конкретная панель — рисуем её кривую, иначе — суммарную.
    """
    import plotly.graph_objects as go

    st.markdown("### 📈 График выработки за сутки")

    fig = go.Figure()

    # Суммарная кривая (всегда показываем серым фоном)
    fig.add_trace(go.Scatter(
        x=df_gen["hour"],
        y=df_gen["generation_kw"],
        mode="lines+markers",
        name="Все панели",
        line=dict(color="#4a90e2", width=3),
        marker=dict(size=8),
    ))

    # Если выбрана панель — рисуем её кривую поверх
    if selected_panel is not None:
        panel_series = [row["panel_values"][selected_panel] for _, row in df_gen.iterrows()]
        fig.add_trace(go.Scatter(
            x=df_gen["hour"],
            y=panel_series,
            mode="lines+markers",
            name=f"Панель {selected_panel + 1}",
            line=dict(color="#ffcc00", width=3, dash="dot"),
            marker=dict(size=8, symbol="square"),
        ))

    fig.update_layout(
        xaxis_title="Час суток (локальное время)",
        yaxis_title="Мощность, кВт",
        xaxis=dict(tickmode="array", tickvals=list(range(0, 24, 3))),
        yaxis=dict(rangemode="tozero"),
        template="plotly_dark",
        height=400,
        margin=dict(l=40, r=20, t=30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)