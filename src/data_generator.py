import os
import numpy as np
import pandas as pd

# 85 Реальных субъектов РФ сопоставленных с их примерными макроэкономическими типами 
# (Богатые(доноры), Обычные(средние), Депрессивные(дотационные))
REGIONS_DB = {
    # ДОНОРЫ (Высокий ВРП, малая безработица)
    "Москва": 'donor', "Санкт-Петербург": 'donor', "Московская область": 'donor', 
    "Ханты-Мансийский АО": 'donor', "Ямало-Ненецкий АО": 'donor', "Тюменская область": 'donor', 
    "Республика Татарстан": 'donor', "Ленинградская область": 'donor', "Свердловская область": 'donor',
    "Сахалинская область": 'donor', "Красноярский край": 'donor', "Самарская область": 'donor',
    "Ненецкий АО": 'donor', "Чукотский АО": 'donor', "Магаданская область": 'donor',
    
    # СЛАБЫЕ / ДОТАЦИОННЫЕ (Низкий ВРП, высокая безработица, большие вливания)
    "Республика Тыва": 'depressed', "Ивановская область": 'depressed', "Курганская область": 'depressed',
    "Республика Ингушетия": 'depressed', "Республика Алтай": 'depressed', "Чеченская Республика": 'depressed',
    "Еврейская АО": 'depressed', "Карачаево-Черкесская Республика": 'depressed', 
    "Псковская область": 'depressed', "Костромская область": 'depressed', "Республика Калмыкия": 'depressed',
    "Кабардино-Балкарская Республика": 'depressed', "Республика Бурятия": 'depressed', "Забайкальский край": 'depressed',
    "Республика Дагестан": 'depressed', "Республика Северная Осетия": 'depressed', "Республика Хакасия": 'depressed',
    "Амурская область": 'depressed', "Республика Адыгея": 'depressed', "Камчатский край": 'depressed'
}

# Остальные 50 регионов будут среднестатистическими (average)
# Мы просто заполняем массив вымышленными именами до 85, если лень писать все.
# Но так как нужен реальный дашборд, опишем еще несколько известных, а остаток забьем как "Область N"
additional_average = [
    "Новосибирская область", "Краснодарский край", "Ростовская область", "Челябинская область",
    "Нижегородская область", "Омская область", "Пермский край", "Воронежская область",
    "Волгоградская область", "Саратовская область", "Приморский край", "Кемеровская область",
    "Алтайский край", "Хабаровский край", "Оренбургская область", "Удмуртская Республика",
    "Белгородская область", "Тульская область", "Пензенская область", "Кировская область",
    "Ярославская область", "Ульяновская область", "Томская область", "Республика Саха (Якутия)",
    "Тверская область", "Вологодская область", "Республика Коми", "Республика Башкортостан",
    "Архангельская область", "Республика Крым", "Севастополь", "Рязанская область",
    "Липецкая область", "Курская область", "Брянская область", "Калининградская область",
    "Мурманская область", "Смоленская область", "Республика Мордовия", "Республика Марий Эл",
    "Владимирская область", "Орловская область", "Республика Карелия", "Тамбовская область",
    "Астраханская область", "Новгородская область", "Республика Чувашия", "Калужская область",
    "Сахалинская область", "Рязанская область"
]

for reg in additional_average:
    if reg not in REGIONS_DB:
        REGIONS_DB[reg] = 'average'

# Отрезаем ровно 85 регионов
final_regions = list(REGIONS_DB.keys())[:85]

def generate_regional_data(start_year=2000, end_year=2025):
    years = list(range(start_year, end_year + 1))
    
    np.random.seed(42)  # Для воспроизводимости
    data = []
    
    for r_name in final_regions:
        r_type = REGIONS_DB[r_name]
        
        # Базовые значения зависят от типа региона
        if r_type == 'donor':
            base_grp = np.random.uniform(800, 1500)
            base_unemp = np.random.uniform(2.0, 4.0)
            subsidies = np.random.uniform(0.1, 5.0)
        elif r_type == 'average':
            base_grp = np.random.uniform(400, 800)
            base_unemp = np.random.uniform(4.0, 7.0)
            subsidies = np.random.uniform(10.0, 30.0)
        else:
            base_grp = np.random.uniform(150, 400)
            base_unemp = np.random.uniform(7.0, 12.0)
            subsidies = np.random.uniform(40.0, 80.0)
            
        for y_idx, year in enumerate(years):
            inflation_factor = 1.0 + (y_idx * 0.06) 
            
            grp = base_grp * inflation_factor * np.random.normal(1.0, 0.02)
            income = grp * np.random.uniform(0.4, 0.6)
            unemp = base_unemp * np.random.normal(1.0, 0.02)
            subs = subsidies * np.random.normal(1.0, 0.01)
            
            migration_pull = (grp / 100) * 2.5 + (income / 100) * 1.5
            migration_push = unemp * (-8.0)
            political_factor = (subs / 10) * 1.2
            
            # Мы добавляем ШУМ np.random.normal(0, 5.0) чтобы данные не выглядели как ровная линия. 
            # Это имитирует реальную жизнь, где происходят неучтенные случайности 
            migration_rate = migration_pull + migration_push + political_factor + np.random.normal(0, 5.0)
            
            data.append({
                'Region_Name': r_name,
                'Region_Type': r_type,
                'Year': year,
                'GRP_per_capita': round(grp, 2),
                'Income_per_capita': round(income, 2),
                'Unemployment_rate': round(unemp, 2),
                'Federal_subsidies': round(subs, 2),
                'Migration_rate': round(migration_rate, 2)
            })
            
    df = pd.DataFrame(data)
    
    os.makedirs(os.path.join("..", "data", "processed"), exist_ok=True)
    out_path = os.path.join("..", "data", "processed", "synthetic_regional_data.csv")
    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Синтетический датасет успешно сгенерирован и сохранен в: {out_path}")
    print(f"Размерность: {df.shape[0]} строк, {df.shape[1]} колонок.")
    print(f"Количество уникальных регионов: {df['Region_Name'].nunique()}")
    
if __name__ == "__main__":
    generate_regional_data()
