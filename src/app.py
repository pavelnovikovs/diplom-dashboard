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
        
        critique = f"<b>🔎 Ретроспективный анализ ИИ за {year} год:</b> "
        if mig < -3:
            critique += f"Зафиксирован мощный отток населения. "
            if unemp > 7.0:
                critique += f"Критическая ошибка властей: допущена высокая безработица ({unemp}%). Следовало бросить все силы на сохранение рабочих мест. "
            if subs < 40 and r_type == 'depressed':
                critique += "Федеральному центру следовало влить экстренные дотации, чтобы погасить социальное напряжение."
        elif mig > 2:
            critique += f"Очень успешный год для региона. "
            if grp > 800:
                critique += "Власти приняли верные корпоративные решения, обеспечившие сверхдоходы ВРП. "
            if subs > 40:
                critique += "Федеральные вливания сработали как отличный социальный магнит."
        else:
            critique += "Регион прошел этот год в режиме выживания. Существенных ошибок нет, но не хватило инвестиционных стимулов для роста."

        detailed = f"Аналитический отчет системы:\nГод: {year}\nТекущие параметры:\nВРП: {grp} тыс. руб.\nДоходы населения: {row['Income_per_capita']} тыс. руб.\nБезработица: {unemp}%\nДотации: {subs} млрд. руб.\n\n"
        if mig < 0:
            detailed += "РЕТРОСПЕКТИВНЫЙ КРИТИЧЕСКИЙ РАЗБОР (ОТТОК НАСЕЛЕНИЯ):\n"
            detailed += "Анализ исторического периода показывает, что регион находился в состоянии демографического спада. Отток работоспособного населения стал прямым следствием управленческих недочетов. "
            if unemp > 5.0:
                detailed += f"Наибольшую политическую ошибку составлял бесконтрольный рост безработицы ({unemp}%), который экспоненциально увеличил переезд молодежи в мегаполисы.\n\n"
            if grp < 600:
                detailed += "Низкий уровень ВРП свидетельствует о системной деградации регионального промышленного комплекса.\n\n"
            detailed += "ОШИБКИ, КОТОРЫХ МОЖНО БЫЛО ИЗБЕЖАТЬ (РЕКОМЕНДАЦИОННЫЙ СЛЕД):\n"
            detailed += "[1] Экономическая пассивность: властям необходимо было запустить налоговые каникулы для экстренного спасения малого и среднего бизнеса.\n\n"
            detailed += "[2] Недостаточное лоббирование: региону не удалось обеспечить целевые федеральные дотации для удержания качества жизни на базовом уровне.\n\n"
            detailed += "[3] Кадровый «вымыв»: катастрофически не хватало региональных грантов, удваивающих выплаты по медицинским и образовательным программам поддержки ради удержания кадров."
        else:
            detailed += "РЕТРОСПЕКТИВНЫЙ АУДИТ УСПЕХА (ПРИТОК НАСЕЛЕНИЯ):\n"
            detailed += "Исторический период можно охарактеризовать как сверхуспешный. Региональное Правительство смогло аккумулировать финансовый профицит и удержать миграционное сальдо. Экономика достигла высокой абсорбционной емкости.\n\n"
            detailed += "ПАРАМЕТРЫ СТРАТЕГИЧЕСКОГО ТРИУМФА:\n"
            detailed += "[1] Инфраструктурный баланс: грамотное управление госзаказом позволило избежать кризиса перенаселения (строительство новых школ и больниц поспевало за приезжающими).\n\n"
            detailed += "[2] Рынок недвижимости: обеспечен масштабный ввод жилья, что демпфировало спекулятивный рост стоимости аренды за квадратный метр.\n\n"
            detailed += "[3] Комфортная среда: фокус на качестве городской экосистемы (транспортные развязки, обустройство общественных пространств) превратил субъект в точку притяжения 'цифровых кочевников'."

        return jsonify({
            'status': 'success',
            'grp': grp,
            'income': row['Income_per_capita'],
            'unemployment': unemp,
            'subsidies': subs,
            'migration_rate': mig,
            'critique': critique,
            'detailed': detailed
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
            
        detailed = f"ПРОГНОЗНЫЙ ОТЧЕТ ИИ:\nГод: {int(year)}\nМоделируемые параметры:\nВРП: {grp} тыс. руб.\nДоходы населения: {income} тыс. руб.\nБезработица: {unemp}%\nДотации: {subsidies} млрд. руб.\n\n"
        if prediction < 0:
            detailed += "СТРАТЕГИЧЕСКИЙ РАЗБОР БУДУЩЕГО (УГРОЗА ОТТОКА):\n"
            detailed += "Анализ макроэкономической модели показывает, что при сохранении целевого вектора регион столкнется с системным демографическим кризисом. Уровень доходов де-факто не компенсирует низкий ВРП.\n\n"
            if unemp > 5.0:
                detailed += f"Особую политическую угрозу представляет структурная безработица ({unemp}%), которая является доминирующим драйвером «выталкивания» населения. Безработица выше 5% гарантирует утечку специалистов в мегаполисы-доноры.\n\n"
            detailed += "РЕКОМЕНДУЕМЫЙ ПЛАН АНТИКРИЗИСНЫХ ДЕЙСТВИЙ ДЛЯ АППАРАТА ГУБЕРНАТОРА:\n"
            detailed += "[1] Экономическая политика: Немедленное развертывание Особых Экономических Зон (ОЭЗ) и преференции инвесторам в обмен на создание высокооплачиваемых рабочих мест.\n\n"
            detailed += "[2] Федеральный GR: Жесткое лоббирование увеличения субвенций. На данный момент текущий уровень дотаций не позволяет масштабировать жизненно важные инфраструктурные стройки.\n\n"
            detailed += "[3] Социальный сектор: Валидация региональных грантов и внедрение собственной субсидированной IТ-ипотеки (под 1-2%) для закрепления молодежи.\n\n"
            detailed += "[4] МСБ: Временное снижение ставок по УСН до 1%, что позволит микропредприятиям выйти из тени и экстренно абсорбировать часть безработных."
        else:
            detailed += "СТРАТЕГИЧЕСКИЙ РАЗБОР БУДУЩЕГО (ПРОГНОЗ ПРИТОКА):\n"
            detailed += "Моделируемая экономическая база демонстрирует феноменальную резистентность и выступает центром притяжения для внутренних мигрантов РФ.\n\n"
            if grp > 800:
                detailed += "Базисом успеха является сильная индустриальная политика: конкурентные доходы полностью перекрывают региональные климатические и социальные риски.\n\n"
            detailed += "ДОЛГОСРОЧНАЯ СТРАТЕГИЯ АППАРАТА ГУБЕРНАТОРА ДЛЯ УДЕРЖАНИЯ ТРЕНДА:\n"
            detailed += "[1] Предотвращение коллапса инфраструктуры: Взрывной миграционный приток неизбежно создаст давление на школы и поликлиники. Необходима проактивная закладка в бюджет строительства соц. объектов через механизмы ГЧП.\n\n"
            detailed += "[2] Рынок жилья: Законодательное ограничение точечной застройки и обязательный переход к КРТ. Если рост цен на покупку жилья и аренду превысит рост зарплат, миграционный вектор развернется в обратную сторону.\n\n"
            detailed += "[3] Транспортный кластер: Анонсирование крупных проектов скоростного транспорта, железнодорожных диаметров или метро для связывания новых спальных микрорайонов с индустриальными кластерами.\n\n"
            detailed += "[4] Цифровизация экономики: Переход от привлечения линейного персонала к закладке IT-кампусов и Наукоградов для концентрации «интеллектуального» и высокомаржинального капитала."

        return jsonify({'status': 'success', 'migration_rate': round(prediction, 2), 'detailed': detailed})
        return jsonify({'status': 'success', 'migration_rate': round(prediction, 2), 'detailed': detailed})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

import random
import difflib

@app.route('/chat', methods=['POST'])
def chat():
    """Эвристический 'ИИ' движок для обработки сообщений чата."""
    data = request.json
    try:
        q = data.get('question', '').lower()
        ctx = data.get('context', {})
        
        region = ctx.get('region', '')
        unemp = float(ctx.get('unemployment', 0) or 0)
        grp = float(ctx.get('grp', 0) or 0)
        subs = float(ctx.get('subsidies', 0) or 0)
        
        # Поиск упямонатого региона в тексте (с учетом возможных опечаток)
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
        messages = []
        
        # Системный промпт для инициализации контекста модели
        system_prompt = (
            f"Ты встроенный ИИ-консультант аналитического дашборда региональной экономики. "
            f"Текущий выбранный регион пользователя: '{region if region else 'Не выбран'}'. "
            f"Текущие параметры, выбранные на ползунках: ВРП = {grp} т.р., Безработица = {unemp}%, Дотации = {subs} млрд руб. "
            f"Общайся свободно, разговорным языком. Если спрашивают про экономику - используй текущие параметры. "
            f"Отвечай кратко, 2-3 предложения. Используй HTML теги <b> и <br> для оформления (не используй Markdown). "
        )

        if found_region and found_region != region:
            system_prompt += f"ВАЖНО: Пользователь в своем сообщении упомянул '{found_region}'. Система автоматически сменила регион на него. Твоя задача — коротко ответить, что ты понял это и переключил графики и данные на {found_region}. Спроси, что конкретно его теперь интересует."

        messages.append({'role': 'system', 'content': system_prompt})
        
        # Интеграция истории переписки
        for msg in history_raw:
            if msg.get('role') in ['user', 'assistant']:
                clean_content = msg.get('content', '').replace('<br>', '\n').replace('<b>', '').replace('</b>', '')
                messages.append({'role': msg['role'], 'content': clean_content})

        import g4f
        # Генерация ответа через LLM
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
        return jsonify({'status': 'error', 'answer': 'Произошла ошибка при анализе макроэкономики.'})

if __name__ == '__main__':
    print("Бэкенд обновлен (ИИ-Чат добавлен). Сервер: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
