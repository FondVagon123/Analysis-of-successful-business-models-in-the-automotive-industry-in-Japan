import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import json

# Імпорт оновлених функцій з data_processor.py
from src.data_processor import (
    load_digital_metrics_data, calculate_kpis, 
    create_mrr_arr_chart, create_churn_arpu_chart,
    create_mrr_forecast
)

# --- 1. Ініціалізація Dash Додатку ---
app = dash.Dash(__name__, external_stylesheets=['assets/styles.css'])

# --- 2. Константа: Дефолтне значення та опції Dropdown (АДАПТОВАНО) ---
DEFAULT_MODEL = 'Авто-Підписка (MaaS/Kinto)'
MODEL_OPTIONS = [
    {'label': 'Авто-Підписка (MaaS/Kinto)', 'value': 'Авто-Підписка (MaaS/Kinto)'},
    {'label': 'Маркетплейс Запчастин', 'value': 'Маркетплейс Запчастин'},
    {'label': 'Connected Services (Дані)', 'value': 'Connected Services (Дані)'}
]

# --- 3. Dash Layout (Структура Сайту) ---
app.layout = html.Div(className='app-container', children=[
    
    # Заголовок (АДАПТОВАНО)
    html.Div(className='header', children=[
        html.H1('Аналітична Платформа: Цифрова Трансформація Автоіндустрії Японії')
    ]),
    
    # --- ПАНЕЛЬ УПРАВЛІННЯ ---
    html.Div(className='control-panel', children=[
        html.Div(style={'width': '30%', 'padding': '10px'}, children=[
            html.Label('Оберіть Цифрову Бізнес-Модель для Аналізу:'),
            dcc.Dropdown(
                id='model-selector-dropdown',
                options=MODEL_OPTIONS,
                value=DEFAULT_MODEL,
                clearable=False
            )
        ]),
        html.Div(style={'width': '60%', 'padding': '10px'}, children=[
            html.Label('Прогноз росту ARR (річний):'),
            dcc.Slider(
                id='growth-rate-slider',
                min=-15,
                max=20,
                step=1,
                value=5, 
                marks={i: f'{i}%' for i in range(-15, 21, 5)}
            )
        ]),
    ]),
    
    # --- Блок KPI (Вихідні дані Callback) ---
    html.Div(className='kpi-row', children=[
        html.Div(className='kpi-card', children=[
            html.H3('MRR (Міс. Дохід, трлн USD)'),
            html.P(id='kpi-mrr', className='kpi-value')
        ]),
        html.Div(className='kpi-card', children=[
            html.H3('ARR (Річ. Дохід, трлн USD)'),
            html.P(id='kpi-arr', className='kpi-value')
        ]),
        html.Div(className='kpi-card', children=[
            html.H3('Середній Churn (%)'),
            html.P(id='kpi-churn', className='kpi-value')
        ]),
        html.Div(className='kpi-card', children=[
            html.H3('LTV (USD, Спрощ.)'),
            html.P(id='kpi-ltv', className='kpi-value')
        ]),
    ]),
    
    # --- СКРИТИЙ DIV: Зберігання завантажених даних ---
    dcc.Store(id='stored-data'), 
    
    # --- Основний Контент: 2 колонки ---
    html.Div(className='content-row', children=[
        
        # --- ЛІВИЙ БЛОК: Динаміка Ключових Метрик ---
        html.Div(className='left-column', children=[
            html.H2(id='left-column-title', children='Динаміка Ключових Метрик (Історія)'),
            
            html.Div(className='card', children=[dcc.Graph(id='graph-mrr')]),
            html.Div(className='card', children=[dcc.Graph(id='graph-churn')]),
            html.Div(className='card', children=[dcc.Graph(id='graph-arpu')]), 
        ]), 
        
        # --- ПРАВИЙ БЛОК: Моделювання ARR ---
        html.Div(className='right-column', children=[
            html.H2('Моделювання та Прогноз ARR'),
            
            html.Div(className='card', children=[
                html.H3('Моделювання Прогнозу ARR'),
                
                # Графік Прогнозу ARR (Інтерактивний)
                html.Div([
                    dcc.Graph(id='graph-arr-forecast'),
                ]),
            ]),
            
            # Історія Динаміки ARR (для порівняння)
            html.Div(className='card', children=[
                dcc.Graph(id='graph-arr-history')
            ]),
            
        ]),
    ]),
    
    # FOOTER
    html.Div(className='footer', children=[
        html.P('Аналітична Платформа: Моделювання цифрових бізнес-моделей. Дані 2015-2024.')
    ])
])


# --- 4. CALLBACK: Динамічне Оновлення Даних при зміні Dropdown ---
@app.callback(
    Output('stored-data', 'data'),
    [Input('model-selector-dropdown', 'value')]
)
def update_data_store(selected_model):
    """Завантажує дані для вибраної моделі та зберігає їх у пам'яті Dash."""
    if not selected_model:
        return {}
    
    # Викликає оновлену функцію load_digital_metrics_data з data_processor.py
    df = load_digital_metrics_data(selected_model)
    
    # Конвертуємо DataFrame у JSON для зберігання
    return df.to_json(date_format='iso', orient='split')


# --- 5. CALLBACK: Оновлення Всіх Елементів (KPI та Графіків) ---
@app.callback(
    [
        # KPI Outputs
        Output('kpi-mrr', 'children'),
        Output('kpi-arr', 'children'),
        Output('kpi-churn', 'children'),
        Output('kpi-ltv', 'children'),
        # Graph Outputs (Історія)
        Output('graph-mrr', 'figure'),
        Output('graph-churn', 'figure'),
        Output('graph-arpu', 'figure'),
        Output('graph-arr-history', 'figure'),
        # Forecast Graph Output
        Output('graph-arr-forecast', 'figure'),
        # Title Output
        Output('left-column-title', 'children'),
    ],
    [
        Input('stored-data', 'data'),      # Залежить від Dropdown (оновлення даних)
        Input('growth-rate-slider', 'value') # Залежить від Слайдера (оновлення прогнозу)
    ]
)
def update_all_elements(jsonified_cleaned_data, growth_rate_percent):
    """
    Головний Callback, який оновлює всі елементи (KPI, Історія, Прогноз)
    при зміні моделі (даних) або слайдера (прогноз).
    """
    if not jsonified_cleaned_data:
        # Повернення заглушок, якщо даних немає
        empty_fig = go.Figure().update_layout(title="Оберіть модель...")
        return (0, 0, 0, 0, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, 'Динаміка Ключових Метрик (Історія)')

    # 1. Завантаження даних з пам'яті (Dash Store)
    df_metrics = pd.read_json(jsonified_cleaned_data, orient='split')
    
    # 2. Розрахунок KPI
    kpi_data = calculate_kpis(df_metrics)
    
    # 3. Побудова Графіків Історії
    mrr_chart = create_mrr_arr_chart(df_metrics, metric='MRR')
    arr_chart_history = create_mrr_arr_chart(df_metrics, metric='ARR').update_layout(title='Історія Динаміки ARR')
    churn_chart = create_churn_arpu_chart(df_metrics, metric='Churn')
    arpu_chart = create_churn_arpu_chart(df_metrics, metric='ARPU')
    
    # 4. Побудова Графіка Прогнозу (Forecast)
    
    # Створення прогнозу
    df_forecast = create_mrr_forecast(df_metrics, growth_rate_percent)
    
    # Створення копії базового графіка (історія ARR)
    fig_forecast = go.Figure(arr_chart_history.to_dict()) 
    fig_forecast.data[0].name = 'Історія ARR' # Перейменовуємо історичний трейс
    
    scenario_name = f'Сценарій ({growth_rate_percent}%)'
    
    if not df_forecast.empty:
        # Додаємо трейс прогнозу
        fig_forecast.add_trace(go.Scatter(
            x=df_forecast['Year'], 
            y=df_forecast['ARR_USD_Trillion'],
            mode='lines+markers',
            name=scenario_name,
            line=dict(color='red', dash='dot')
        ))
    
    fig_forecast.update_layout(
        title='Прогноз ARR (Річний Дохід) vs Факт',
        legend_title_text='Легенда',
        transition_duration=500,
        yaxis_title='Дохід (трлн USD)'
    )
    
    # 5. Повернення всіх вихідних даних
    
    # Повернення KPI (як текст)
    kpi_mrr = kpi_data.get('MRR (трлн USD)', 0)
    kpi_arr = kpi_data.get('ARR (трлн USD)', 0)
    kpi_churn = kpi_data.get('Середній Churn (%)', 0)
    kpi_ltv = kpi_data.get('LTV (USD)', 0)
    
    return (
        kpi_mrr, kpi_arr, kpi_churn, kpi_ltv,
        mrr_chart, churn_chart, arpu_chart, arr_chart_history,
        fig_forecast,
        'Динаміка Ключових Метрик (Історія)' # Заголовок
    )


# --- 6. Запуск Додатку ---
if __name__ == '__main__':
    # Використовуємо app.run() для сучасних версій Dash
    app.run(debug=True, use_reloader=False)