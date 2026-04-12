import os
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ==========================================
# 1. Загрузка и подготовка данных
# ==========================================
def load_and_preprocess_data(filepath):
    print("Загрузка данных...")
    df = pd.read_csv(filepath)
    
    # Отделяем целевую переменную
    y = df['Migration_rate'].values
    
    # Категориальные (Region_Type) и числовые признаки
    categorical_cols = ['Region_Type']
    numeric_cols = ['Year', 'GRP_per_capita', 'Income_per_capita', 'Unemployment_rate', 'Federal_subsidies']
    
    # One-Hot Encoding для типа региона
    encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
    encoded_cat = encoder.fit_transform(df[categorical_cols])
    
    # Масштабирование числовых признаков (очень важно для нейросетей)
    scaler = StandardScaler()
    scaled_num = scaler.fit_transform(df[numeric_cols])
    
    # Объединяем фичи
    X = np.hstack((scaled_num, encoded_cat))
    
    data_split = train_test_split(X, y, test_size=0.2, random_state=42)
    return data_split, scaler, encoder

# ==========================================
# 2. Архитектура Нейронной Сети
# ==========================================
class MigrationPredictor(nn.Module):
    def __init__(self, input_dim):
        super(MigrationPredictor, self).__init__()
        # Полносвязная сеть с 3 скрытыми слоями
        self.network = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.BatchNorm1d(64),
            nn.Dropout(0.2), # Защита от переобучения
            
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.BatchNorm1d(32),
            
            nn.Linear(32, 16),
            nn.ReLU(),
            
            nn.Linear(16, 1) # Один выход - коэффициент миграции
        )

    def forward(self, x):
        return self.network(x)

# ==========================================
# 3. Цикл обучения и сохранение модели
# ==========================================
def train_model():
    data_path = os.path.join("..", "data", "processed", "synthetic_regional_data.csv")
    if not os.path.exists(data_path):
        print(f"Файл не найден: {data_path}. Сначала запустите data_generator.py")
        return
        
    (X_train, X_test, y_train, y_test), scaler, encoder = load_and_preprocess_data(data_path)
    
    # Конвертация в тензоры PyTorch
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.FloatTensor(y_train).view(-1, 1) # [N, 1]
    X_test_t = torch.FloatTensor(X_test)
    y_test_t = torch.FloatTensor(y_test).view(-1, 1)
    
    # Инициализация модели, функции потерь и оптимизатора
    model = MigrationPredictor(input_dim=X_train.shape[1])
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    
    epochs = 150
    print("Начало обучения нейросети...")
    
    for epoch in range(epochs):
        model.train()
        
        # Forward pass
        predictions = model(X_train_t)
        loss = criterion(predictions, y_train_t)
        
        # Обратное распространение ошибки (Backprop)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        if (epoch + 1) % 30 == 0:
            print(f"Эпоха [{epoch+1}/{epochs}], Loss (MSE): {loss.item():.4f}")
            
    # ==========================================
    # 4. Оценка модели (Метрики)
    # ==========================================
    model.eval()
    with torch.no_grad():
        test_preds = model(X_test_t).numpy()
        
    mae = mean_absolute_error(y_test, test_preds)
    mse = mean_squared_error(y_test, test_preds)
    r2 = r2_score(y_test, test_preds)
    
    print("\n--- РЕЗУЛЬТАТЫ ВАЛИДАЦИИ НА ТЕСТОВОЙ ВЫБОРКЕ ---")
    print(f"Средняя абсолютная ошибка (MAE): {mae:.4f}")
    print(f"Среднеквадратичная ошибка (MSE): {mse:.4f}")
    print(f"Коэффициент детерминации (R^2):  {r2:.4f}")
    
    # ==========================================
    # 5. Экспорт (Инференс)
    # ==========================================
    os.makedirs('export', exist_ok=True)
    torch.save(model.state_dict(), 'export/model.pth')
    joblib.dump(scaler, 'export/scaler.pkl')
    joblib.dump(encoder, 'export/encoder.pkl')
    print("\nМодель и препроцессоры успешно сохранены в папке 'export'!")

if __name__ == "__main__":
    train_model()
