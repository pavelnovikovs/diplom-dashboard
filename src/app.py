from flask import Flask, render_template, request, jsonify
import torch
import joblib
import numpy as np
import pandas as pd
import os
from model import MigrationPredictor

app = Flask(__name__)

# Загружаем подготовленные файлы ИИ
if not os.path.exists('export/model.pth'):
    print("ВНИМАНИЕ: Сначала запустите model.py для обучения сети")
    exit(1)

scaler = joblib.load('export/scaler.pkl')
encoder = joblib.load('export/encoder.pkl')

input_dim = scaler.mean_.shape[0] + sum(len(c) for c in encoder.categories_)
nn_model = MigrationPredictor(input_dim)
nn_model.load_state_dict(torch.load('export/model.pth'))
nn_model.eval()

# Загружаем исторические «факты Росстата»
df_history = pd.read_csv('../data/processed/synthetic_regional_data.csv')
regions_meta = df_history[['Region_Name', 'Region_Type']].drop_duplicates().to_dict('records')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_regions', methods=['GET'])
def get_regions():
    return jsonify({'status': 'success', 'regions': regions_meta})

@app.route('/get_history', methods=['POST'])
def get_history():
    data = request.json
    region = data.get('region')
    year = int(data.get('year'))
    
    record = df_history[(df_history['Region_Name'] == region) & (df_history['Year'] == year)]
    if not record.empty:
        row = record.iloc[0]
        
        mig = row['Migration_rate']
        unemp = row['Unemployment_rate']
        grp = row['GRP_per_capita']
        subs = row['Federal_subsidies']
        r_type = row['Region_Type']
        
        return jsonify({
            'status': 'success',
            'grp': grp,
            'income': row['Income_per_capita'],
            'unemployment': unemp,
            'subsidies': subs,
            'migration_rate': mig,
            'region': region,
            'year': year
        })
    return jsonify({'status': 'error'})

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json
    try:
        region_type = data['region_type'] 
        year = float(data['year'])
        grp = float(data['grp'])
        income = float(data['income'])
        unemp = float(data['unemployment'])
        subsidies = float(data['subsidies'])
        
        cat_encoded = encoder.transform([[region_type]])
        num_scaled = scaler.transform([[year, grp, income, unemp, subsidies]])
        
        X_infer = np.hstack((num_scaled, cat_encoded))
        X_tensor = torch.FloatTensor(X_infer)
        
        with torch.no_grad():
            prediction = nn_model(X_tensor).item()
            
        return jsonify({
            'status': 'success',
            'migration_rate': round(prediction, 2),
            'year': int(year),
            'grp': grp,
            'income': income,
            'unemployment': unemp,
            'subsidies': subsidies
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

import g4f
import random
import difflib

@app.route('/generate_report', methods=['POST'])
def generate_report():
    """RAG-архитектура: K-NN и корреляция из датасета → языковая модель генерирует уникальный отчёт."""
    data = request.json
    try:
        region = data.get('region', 'Не выбран')
        year = int(data.get('year', 2026))
        grp = float(data.get('grp', 0))
        income = float(data.get('income', 0))
        unemp = float(data.get('unemployment', 0))
        subs = float(data.get('subsidies', 0))
        migration_rate = float(data.get('migration_rate', 0))
        mode = data.get('mode', 'forecast')

        df = df_history.copy()

        # K-NN: ищем похожие регионы в датасете по нормализованному расстоянию
        for col, val in [('GRP_per_capita', grp), ('Income_per_capita', income),
                         ('Unemployment_rate', unemp), ('Federal_subsidies', subs)]:
            std = df[col].std()
            df[f'{col}_diff'] = ((df[col] - val) / std) ** 2

        df['distance'] = (df['GRP_per_capita_diff'] + df['Income_per_capita_diff'] +
                          df['Unemployment_rate_diff'] + df['Federal_subsidies_diff']) ** 0.5

        similar = df.nsmallest(8, 'distance')
        pos_count = int((similar['Migration_rate'] > 0).sum())
        neg_count = int((similar['Migration_rate'] < 0).sum())
        avg_mig = similar['Migration_rate'].mean()

        # Корреляционный анализ: ранжируем факторы по силе влияния на миграцию
        corr = df_history[['GRP_per_capita', 'Income_per_capita',
                            'Unemployment_rate', 'Federal_subsidies',
                            'Migration_rate']].corr()['Migration_rate'].drop('Migration_rate')
        corr_sorted = corr.abs().sort_values(ascending=False)

        name_map = {
            'GRP_per_capita': 'ВРП на душу населения',
            'Income_per_capita': 'Среднедушевые доходы',
            'Unemployment_rate': 'Безработица',
            'Federal_subsidies': 'Федеральные дотации'
        }

        avg_grp = df_history['GRP_per_capita'].mean()
        avg_unemp = df_history['Unemployment_rate'].mean()
        avg_subs = df_history['Federal_subsidies'].mean()
        avg_income = df_history['Income_per_capita'].mean()

        # Формируем текст с реальными аналогами для языковой модели
        analogs_text = "\n".join([
            f"  - {row['Region_Name']} ({int(row['Year'])}): коэфф. {row['Migration_rate']:+.2f}, "
            f"ВРП={row['GRP_per_capita']:.0f} т.р., безработица={row['Unemployment_rate']:.1f}%"
            for _, row in similar.head(5).iterrows()
        ])

        drivers_text = "\n".join([
            f"  - {name_map[k]}: r={corr[k]:.2f}"
            for k in corr_sorted.index
        ])

        mode_label = "ретроспективный анализ (факт Росстата)" if mode == 'history' else "прогноз нейросети PyTorch"

        # RAG-промпт: языковая модель получает реальные данные из датасета и генерирует уникальный текст
        prompt = (
            f"Ты — аналитическая система поддержки принятия решений для региональных чиновников России. "
            f"Твоя задача — давать конкретные, нешаблонные советы на основе реальных данных.\n\n"
            f"ВХОДНЫЕ ДАННЫЕ ({mode_label}):\n"
            f"Регион: {region}, год: {year}\n"
            f"Прогноз миграции: {migration_rate:+.2f} чел. на 10 000 жителей "
            f"({'ПРИТОК' if migration_rate > 0 else 'ОТТОК'} населения)\n"
            f"ВРП на душу: {grp} т.р. (среднее по РФ: {avg_grp:.0f} т.р.)\n"
            f"Среднедушевые доходы: {income} т.р. (среднее: {avg_income:.0f} т.р.)\n"
            f"Безработица: {unemp}% (среднее: {avg_unemp:.1f}%)\n"
            f"Федеральные дотации: {subs} млрд. (среднее: {avg_subs:.0f} млрд.)\n\n"
            f"ДАННЫЕ ИЗ ДАТАСЕТА РОССТАТА — регионы с похожими условиями ({pos_count} дали приток, {neg_count} — отток):\n"
            f"{analogs_text}\n\n"
            f"КОРРЕЛЯЦИЯ ПАРАМЕТРОВ С МИГРАЦИЕЙ (статистический анализ датасета):\n"
            f"{drivers_text}\n\n"
            f"ВАЖНОЕ ОГРАНИЧЕНИЕ МОДЕЛИ: учтены только экономические факторы. "
            f"На миграцию также влияют: политическая стабильность, уровень коррупции, "
            f"экологическая обстановка, качество медицины и образования, транспортная доступность. "
            f"Упомяни это ограничение в конце отчёта.\n\n"
            f"Составь аналитический отчёт. Объясни конкретно, почему модель дала такой прогноз — ссылайся на цифры. "
            f"Сравни с историческими аналогами из датасета. "
            f"Дай 3-4 нешаблонных совета именно для этого региона с этими показателями. "
            f"Используй HTML: <b> для заголовков, <br> для переносов. Не используй Markdown. "
            f"Пиши живым языком, как будто говоришь с губернатором лично."
        )

        response = g4f.ChatCompletion.create(
            model="gpt-4",
            messages=[{'role': 'user', 'content': prompt}]
        )

        return jsonify({'status': 'success', 'report': response})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/chat', methods=['POST'])
def chat():
    """RAG-чатбот: реальные данные из датасета по региону передаются в языковую модель."""
    data = request.json
    try:
        q = data.get('question', '').lower()
        ctx = data.get('context', {})

        region = ctx.get('region', '')
        unemp = float(ctx.get('unemployment', 0) or 0)
        grp = float(ctx.get('grp', 0) or 0)
        subs = float(ctx.get('subsidies', 0) or 0)

        # Поиск упомянутого региона в тексте (с учётом возможных опечаток)
        found_region = None
        q_words = q.replace(',', '').replace('.', '').replace('-', ' ').split()

        for r in regions_meta:
            r_name = r['Region_Name'].lower()
            region_first_word = r_name.split()[0]

            if region_first_word in q or r_name in q:
                found_region = r['Region_Name']
                break

            for w in q_words:
                if len(w) > 4:
                    if difflib.get_close_matches(w, [region_first_word], n=1, cutoff=0.75):
                        found_region = r['Region_Name']
                        break

            if found_region:
                break

        history_raw = data.get('history', [])

        # RAG: вытаскиваем реальную историческую статистику по активному региону из датасета
        active_region = found_region if (found_region and found_region != region) else region
        region_stats = ""
        if active_region:
            region_data = df_history[df_history['Region_Name'] == active_region]
            if not region_data.empty:
                last_rows = region_data.sort_values('Year').tail(3)
                region_stats = f"\nСТАТИСТИКА ПО РЕГИОНУ '{active_region}' ИЗ ДАТАСЕТА:\n"
                for _, row in last_rows.iterrows():
                    d = "приток" if row['Migration_rate'] > 0 else "отток"
                    region_stats += (
                        f"  {int(row['Year'])} г.: миграция {row['Migration_rate']:+.2f} ({d}), "
                        f"ВРП={row['GRP_per_capita']:.0f} т.р., безраб.={row['Unemployment_rate']:.1f}%, "
                        f"дотации={row['Federal_subsidies']:.0f} млрд.\n"
                    )

        # Системный контекст с реальными данными из датасета (RAG)
        system_context = (
            f"[КОНТЕКСТ СИСТЕМЫ — НЕ ЦИТИРУЙ ЭТОТ ТЕКСТ НАПРЯМУЮ:\n"
            f"Ты — аналитический ИИ-консультант дашборда региональной политики России. "
            f"Помогаешь чиновникам и аналитикам принимать решения по управлению миграцией.\n"
            f"Текущий регион на дашборде: '{region if region else 'не выбран'}'.\n"
            f"Параметры на ползунках: ВРП={grp} т.р., Безработица={unemp}%, Дотации={subs} млрд.\n"
            f"{region_stats}"
            f"ВАЖНО: модель учитывает только экономические факторы. "
            f"Политические, экологические и социальные факторы (коррупция, медицина, транспорт) в текущей версии не включены.\n"
            f"Отвечай разговорным языком, кратко (2-4 предложения). "
            f"Используй реальные цифры из контекста. HTML: <b> и <br>. Без Markdown.]\n"
        )

        if found_region and found_region != region:
            system_context += f"[Пользователь упомянул '{found_region}' — регион уже переключён системой. Подтверди коротко.]\n"

        # Сборка истории сообщений
        messages = []
        for msg in history_raw:
            if msg.get('role') in ['user', 'assistant']:
                clean = msg.get('content', '').replace('<br>', '\n').replace('<b>', '').replace('</b>', '')
                messages.append({'role': msg['role'], 'content': clean})

        # Подмешиваем контекст с реальными данными в последний вопрос
        if not messages:
            messages.append({'role': 'user', 'content': system_context + q})
        else:
            messages[-1]['content'] = system_context + "\nВопрос: " + messages[-1]['content']

        response = g4f.ChatCompletion.create(
            model="gpt-4",
            messages=messages
        )

        payload = {'status': 'success', 'answer': response}

        # Передача команды смены региона фронтенду
        if found_region and found_region != region:
            payload['set_region'] = found_region

        return jsonify(payload)
    except Exception as e:
        return jsonify({'status': 'error', 'answer': 'Произошла ошибка при обработке запроса.'})

if __name__ == '__main__':
    print("Сервер запущен: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
