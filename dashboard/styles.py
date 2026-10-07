# dashboard/styles.py
"""CSS-стили для дашборда."""
import streamlit as st


def inject_css():
    st.markdown(
        """
        <style>
        /* Контейнер станции */
        .station-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            padding: 16px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            border-radius: 16px;
            margin-bottom: 16px;
        }
        /* Одна солнечная панель */
        .solar-panel {
            background: linear-gradient(135deg, #2c3e50 0%, #4a6072 100%);
            border: 2px solid #5a7a9a;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            color: #ffffff;
            cursor: pointer;
            transition: all 0.2s;
            min-height: 90px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .solar-panel:hover {
            transform: translateY(-3px);
            border-color: #ffcc00;
            box-shadow: 0 6px 14px rgba(255, 204, 0, 0.4);
        }
        .solar-panel.selected {
            border-color: #ffcc00;
            background: linear-gradient(135deg, #4a6072 0%, #6a8092 100%);
            box-shadow: 0 0 20px rgba(255, 204, 0, 0.6);
        }
        .panel-label {
            font-size: 0.75rem;
            opacity: 0.7;
        }
        .panel-value {
            font-size: 1.05rem;
            font-weight: 700;
            color: #ffcc00;
            margin-top: 4px;
        }
        /* Карточка итога */
        .summary-card {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 12px;
            padding: 20px;
            color: #ffffff;
            border: 1px solid #2a5298;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }
        .summary-label {
            font-size: 0.85rem;
            opacity: 0.65;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .summary-value {
            font-size: 2.2rem;
            font-weight: 800;
            color: #ffcc00;
            margin-top: 4px;
        }
        .summary-unit {
            font-size: 1rem;
            opacity: 0.7;
            margin-left: 6px;
        }
        .weather-item {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            color: #e0e0e0;
        }
        .weather-item:last-child { border-bottom: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )