import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go # Додано імпорт go для create_mrr_forecast

# !!! КОНСТАНТА: Шлях до папки з даними !!!
DATA_FOLDER = 'data/'
SEPARATOR = ',' 

# --- 1. Функції для Завантаження та Обробки Цифрових Даних (ОНОВЛЕНО) ---
def load_digital_metrics_data(model_name: str):
    """
    Динамічно завантажує та очищує дані для вибраної бізнес-моделі 
    з адаптованими назвами для Автоіндустрії.
    """
    # Створення повного шляху до файлу на основі вибраної моделі
    if model_name == 'Авто-Підписка (MaaS/Kinto)':
        file_path = DATA_FOLDER + 'Auto_Subscription_Kinto.csv'
    elif model_name == 'Маркетплейс Запчастин':
        file_path = DATA_FOLDER + 'Auto_Marketplace_Parts.csv'
    elif model_name == 'Connected Services (Дані)':
        file_path = DATA_FOLDER + 'Connected_Services_Data.csv'
    else:
        # Повертаємо пустий DataFrame, якщо модель не знайдено
        return pd.DataFrame() 
    
    print(f"Завантаження даних для моделі: {model_name} з {file_path}")

    try:
        df = pd.read_csv(file_path, sep=SEPARATOR, encoding='utf-8')
    except FileNotFoundError:
        print(f"Помилка: Файл {file_path} не знайдено.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Помилка при читанні CSV: {e}")
        return pd.DataFrame()

    # Очищення та конвертація числових колонок
    cols_to_clean = ['Year', 'Total_Customers', 'New_Customers', 'Churned_Customers', 'Avg_Monthly_Price_USD']
    for col in cols_to_clean:
        # Агресивне очищення: видаляємо все, окрім цифр і крапки
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d\.]', '', regex=True), errors='coerce')

    df.dropna(subset=['Year', 'Total_Customers', 'Avg_Monthly_Price_USD'], inplace=True)
    df['Year'] = df['Year'].astype('Int64')
    
    # ------------------ РОЗРАХУНОК МЕТРИК ------------------
    
    # 1. MRR (Monthly Recurring Revenue)
    # Ділимо на 10^12 для конвертації у трильйони USD для зручності відображення
    df['MRR_USD_Trillion'] = (df['Total_Customers'] * df['Avg_Monthly_Price_USD']) / 10**12 
    
    # 2. ARR (Annual Recurring Revenue)
    df['ARR_USD_Trillion'] = df['MRR_USD_Trillion'] * 12
    
    # 3. Churn Rate (Річний відтік клієнтів)
    df['Churn_Rate_Percent'] = (df['Churned_Customers'] / df['Total_Customers']) * 100
    
    # 4. ARPU (Average Revenue Per User)
    df['ARPU_USD'] = df['Avg_Monthly_Price_USD'] # У даному випадку це і є ARPU

    # 5. LTV (Lifetime Value) - Спрощена формула: Avg_Monthly_Revenue / Monthly_Churn_Rate
    # Оскільки у нас річний Churn, для спрощення розрахунку використовуємо його.
    df['LTV_USD'] = df['Avg_Monthly_Price_USD'] / (df['Churn_Rate_Percent'] / 100.0) 
    
    return df

# --- 2. Функції для Розрахунку KPI (Single Value) ---
def calculate_kpis(df):
    """
    Розраховує ключові показники для відображення в картках KPI (на основі останнього року).
    """
    if df.empty:
        return {'MRR (трлн USD)': 0, 'ARR (трлн USD)': 0, 'Середній Churn (%)': 0, 'LTV (USD)': 0}

    latest_data = df.iloc[-1]
    
    # Середній Churn Rate за весь період
    avg_churn = df['Churn_Rate_Percent'].mean()

    kpi = {
        # Використовуємо високу точність (6 знаків), щоб уникнути відображення "0.00"
        'MRR (трлн USD)': f"{latest_data['MRR_USD_Trillion']:.6f}",
        'ARR (трлн USD)': f"{latest_data['ARR_USD_Trillion']:.6f}",
        'Середній Churn (%)': f"{avg_churn:.2f}",
        'LTV (USD)': f"{latest_data['LTV_USD']:.0f}"
    }
    
    return kpi

# --- 3. Функції для Побудови Графіків ---

def create_mrr_arr_chart(df, metric='MRR'):
    """Створює лінійний графік MRR або ARR."""
    if df.empty:
        return px.line(title=f"Немає даних для {metric}")
        
    y_col = 'MRR_USD_Trillion' if metric == 'MRR' else 'ARR_USD_Trillion'
    title = 'Динаміка Місячного Регулярного Доходу (MRR)' if metric == 'MRR' else 'Динаміка Річного Регулярного Доходу (ARR)'
    
    fig = px.line(
        df,
        x='Year',
        y=y_col,
        title=title,
        labels={y_col: 'Дохід (трлн USD)', 'Year': 'Рік'},
        markers=True,
        height=500
    )
    fig.update_traces(line_color='#007bff')
    return fig

def create_churn_arpu_chart(df, metric='Churn'):
    """Створює графік Churn Rate або ARPU."""
    if df.empty:
        return px.line(title=f"Немає даних для {metric}")
        
    if metric == 'Churn':
        y_col = 'Churn_Rate_Percent'
        title = 'Динаміка Відтоку Клієнтів (Churn Rate)'
        color = '#dc3545'
        labels = {y_col: 'Відсоток Відтоку (%)', 'Year': 'Рік'}
    else:
        y_col = 'ARPU_USD'
        title = 'Середній Дохід на Користувача (ARPU)'
        color = '#28a745'
        labels = {y_col: 'Дохід (USD)', 'Year': 'Рік'}

    fig = px.line(
        df,
        x='Year',
        y=y_col,
        title=title,
        labels=labels,
        markers=True,
        height=500
    )
    fig.update_traces(line_color=color)
    return fig

# --- 4. Функція для Моделювання Прогнозу ---
def create_mrr_forecast(df, arr_growth_rate_percent, forecast_years=5):
    """
    Створює прогноз ARR на основі останнього року та заданої ставки зростання.
    """
    if df.empty or 'ARR_USD_Trillion' not in df.columns:
        # Повертаємо пустий об'єкт go.Figure, щоб уникнути помилки в app.py
        empty_fig = go.Figure()
        empty_fig.update_layout(title="Необхідно вибрати бізнес-модель.")
        return pd.DataFrame()

    last_year = df['Year'].max()
    # Використання .iloc[0] для безпечного отримання значення
    last_arr_value = df[df['Year'] == last_year]['ARR_USD_Trillion'].iloc[0] 
    
    growth_rate = 1 + (arr_growth_rate_percent / 100.0)
    
    forecast_data = []
    current_arr_value = last_arr_value

    for i in range(1, forecast_years + 1):
        forecast_year = last_year + i
        current_arr_value *= growth_rate
        
        forecast_data.append({
            'Year': forecast_year, 
            'ARR_USD_Trillion': current_arr_value
        })
        
    df_forecast = pd.DataFrame(forecast_data)
    
    return df_forecast