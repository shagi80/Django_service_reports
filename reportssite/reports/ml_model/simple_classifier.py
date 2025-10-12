# simple_classifier.py
import pandas as pd
import numpy as np
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from catboost import CatBoostClassifier
import pickle
import json
import os

class TwoLevelClassifier:
    def __init__(self):
        # Векторизатор для уровня групп
        self.group_vectorizer = TfidfVectorizer(
            max_features=2000,
            min_df=2,
            max_df=0.9,
            ngram_range=(1, 2),
            stop_words=['и', 'в', 'не', 'на', 'с', 'по', 'у', 'из', 'от']
        )
        
        # Векторизаторы для уровня кодов (будут создаваться для каждой группы)
        self.code_vectorizers = {}
        
        # Модели
        self.group_model = None
        self.code_models = {}  # Модели для каждой группы
        
        # Маппинги
        self.group_mappings = {}  # group_name -> group_id
        self.code_mappings = {}   # code_name -> code_id
        self.codes_by_group = {}  # group_name -> [code_names]
        
        # Обратные маппинги
        self.id_to_group = {}  # group_id -> group_name
        self.id_to_code = {}   # code_id -> code_name
        
        # Маппинги для кодов внутри групп
        self.group_code_mappings = {}  # group_name -> {code_name -> code_id}
        self.group_id_to_code = {}     # group_name -> {code_id -> code_name}
    
    def train(self, df, text_column='problem_lemmatized', 
              group_column='group_id', code_column='code_id'):
        """
        Обучение двухуровневой модели
        """
        print("🎯 НАЧИНАЕМ ОБУЧЕНИЕ ДВУХУРОВНЕВОЙ МОДЕЛИ...")
        
        # Уровень 1: Обучение классификатора групп
        print("\n📊 УРОВЕНЬ 1: ОБУЧЕНИЕ КЛАССИФИКАТОРА ГРУПП...")
        self._train_group_classifier(df, text_column, group_column)
        
        # Уровень 2: Обучение классификаторов кодов для каждой группы
        print("\n📊 УРОВЕНЬ 2: ОБУЧЕНИЕ КЛАССИФИКАТОРОВ КОДОВ...")
        self._train_code_classifiers(df, text_column, group_column, code_column)
        
        print("✅ ОБУЧЕНИЕ ЗАВЕРШЕНО!")
    
    def _train_group_classifier(self, df, text_column, group_column):
        """Обучение классификатора групп"""
        # Разделяем данные для групп
        X_train, X_test, y_train, y_test = train_test_split(
            df[text_column], 
            df[group_column], 
            test_size=0.2, 
            random_state=42,
            stratify=df[group_column]
        )
        
        print(f"📚 Обучающая выборка групп: {len(X_train)} примеров")
        print(f"📚 Тестовая выборка групп: {len(X_test)} примеров")
        print(f"📊 Уникальные группы: {df[group_column].nunique()}")
        
        # Векторизация для групп
        print("🔤 Векторизация текстов для групп...")
        X_train_vec = self.group_vectorizer.fit_transform(X_train)
        X_test_vec = self.group_vectorizer.transform(X_test)
    
        # ПРЕОБРАЗУЕМ В ПЛОТНЫЙ ФОРМАТ для CatBoost
        X_train_vec = X_train_vec.toarray()
        X_test_vec = X_test_vec.toarray()
        
        print(f"📐 Размерность признаков групп: {X_train_vec.shape}")
        
        # Расчет весов классов для балансировки
        class_weights = self._calculate_class_weights(y_train)
        
        # Обучение модели групп
        print("🤖 Обучение CatBoost для групп...")
        self.group_model = CatBoostClassifier(
            iterations=100,
            learning_rate=0.15,
            depth=6,
            loss_function='MultiClass',
            class_weights=class_weights,
            verbose=50,
            random_state=42,
            early_stopping_rounds=20
        )
        
        self.group_model.fit(
            X_train_vec, y_train,
            eval_set=(X_test_vec, y_test),
            verbose=50
        )
        
        # Оценка модели групп
        y_pred = self.group_model.predict(X_test_vec)
        accuracy = accuracy_score(y_test, y_pred)
        print(f"🎯 Точность классификации групп: {accuracy:.3f}")
    
    def _train_code_classifiers(self, df, text_column, group_column, code_column):
        """Обучение классификаторов кодов для каждой группы"""
        unique_groups = df[group_column].unique()
        
        for group_id in unique_groups:
            group_data = df[df[group_column] == group_id]
            group_name = self.id_to_group[group_id]
            
            # Получаем коды, которые действительно принадлежат этой группе
            valid_codes_for_group = self.codes_by_group.get(group_name, [])
            group_data = group_data[group_data[code_column].isin(
                [self.code_mappings.get(code) for code in valid_codes_for_group if code in self.code_mappings]
            )]
            
            # Проверяем количество уникальных классов в группе
            unique_classes = group_data[code_column].nunique()
            
            if len(group_data) < 10 or unique_classes < 2:
                print(f"⚠️  Пропускаем группу {group_name}: {len(group_data)} примеров, {unique_classes} классов")
                continue
            
            print(f"\n🔧 Обучение модели для группы {group_name} ({len(group_data)} примеров, {unique_classes} классов)...")
            
            # Создаем маппинг кодов для этой группы
            group_codes = group_data[code_column].unique()
            group_code_mapping = {code_id: i for i, code_id in enumerate(group_codes)}
            reverse_group_code_mapping = {i: self.id_to_code[code_id] for code_id, i in group_code_mapping.items()}
            
            self.group_code_mappings[group_name] = group_code_mapping
            self.group_id_to_code[group_name] = reverse_group_code_mapping
            
            # Подготавливаем данные с новыми маппингами
            group_data = group_data.copy()
            group_data['mapped_code_id'] = group_data[code_column].map(group_code_mapping)
            
            # Разделяем данные для этой группы
            X_train, X_test, y_train, y_test = train_test_split(
                group_data[text_column], 
                group_data['mapped_code_id'], 
                test_size=0.3, 
                random_state=42,
                stratify=group_data['mapped_code_id']
            )
            
            # Создаем векторзатор для этой группы
            group_vectorizer = TfidfVectorizer(
                max_features=500,
                min_df=3,
                max_df=0.8,
                ngram_range=(1, 2)
            )
            
            # Векторизация
            X_train_vec = group_vectorizer.fit_transform(X_train)
            X_test_vec = group_vectorizer.transform(X_test)
    
            # ПРЕОБРАЗУЕМ В ПЛОТНЫЙ ФОРМАТ
            X_train_vec = X_train_vec.toarray()
            X_test_vec = X_test_vec.toarray()
            
            # Сохраняем векторзатор
            self.code_vectorizers[group_name] = group_vectorizer
            
            # Расчет весов классов
            if len(np.unique(y_train)) > 1:
                class_weights = self._calculate_class_weights(y_train)
            else:
                class_weights = None
            
            # Обучение модели для группы
            code_model = CatBoostClassifier(
                iterations=80,
                learning_rate=0.1,
                depth=6,
                loss_function='MultiClass',
                class_weights=class_weights,
                verbose=False,
                random_state=42,
                early_stopping_rounds=15
            )
            
            code_model.fit(
                X_train_vec, y_train,
                eval_set=(X_test_vec, y_test),
                verbose=False
            )
            
            # Сохраняем модель
            self.code_models[group_name] = code_model
            
            # Оценка
            y_pred = code_model.predict(X_test_vec)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Исправление: преобразуем y_pred в плоский массив
            y_pred_flat = y_pred.flatten()
            predicted_codes = [reverse_group_code_mapping.get(int(idx), "UNKNOWN") for idx in y_pred_flat]
            
            print(f"   ✅ Группа {group_name}: точность {accuracy:.3f}")
            print(f"   📋 Коды в группе: {list(reverse_group_code_mapping.values())}")
    
    def _calculate_class_weights(self, y_train):
        """Расчет весов классов для балансировки"""
        class_counts = np.bincount(y_train)
        total_samples = len(y_train)
        n_classes = len(class_counts)
        
        weights = total_samples / (n_classes * class_counts)
        return list(weights)
    
    def predict(self, problem_text, top_n_groups=3, top_n_codes=3):
        """
        Предсказание кода неисправности по тексту
        """
        if self.group_model is None:
            raise ValueError("❌ Модель не обучена! Сначала вызовите train()")
        
        # Очистка входного текста
        cleaned_text = self._clean_text(problem_text)
        
        # Уровень 1: Предсказание группы
        group_vector = self.group_vectorizer.transform([cleaned_text])
        group_vector = group_vector.toarray()
        group_probs = self.group_model.predict_proba(group_vector)[0]
        
        # Топ-N наиболее вероятных групп
        top_group_indices = np.argsort(group_probs)[-top_n_groups:][::-1]
        
        predictions = []
        
        for group_idx in top_group_indices:
            if group_probs[group_idx] > 0.05:
                group_name = self.id_to_group[group_idx]
                group_confidence = group_probs[group_idx]
                
                # Уровень 2: Предсказание кода внутри группы
                code_predictions = self._predict_code_in_group(
                    cleaned_text, group_name, top_n_codes
                )
                
                for code_pred in code_predictions:
                    # Проверяем, что код действительно принадлежит группе
                    if code_pred['code'].startswith(group_name):
                        overall_confidence = group_confidence * code_pred['confidence']
                        
                        predictions.append({
                            'group': group_name,
                            'group_confidence': float(group_confidence),
                            'code': code_pred['code'],
                            'code_confidence': float(code_pred['confidence']),
                            'overall_confidence': float(overall_confidence),
                            'confidence_percent': f"{overall_confidence*100:.1f}%",
                            'valid': True
                        })
                    else:
                        print(f"⚠️  Обнаружен некорректный код: {code_pred['code']} в группе {group_name}")
        
        # Сортируем по общей уверенности
        predictions.sort(key=lambda x: x['overall_confidence'], reverse=True)
        return predictions[:top_n_codes]
    
    def _predict_code_in_group(self, cleaned_text, group_name, top_n_codes):
        """Предсказание кода внутри конкретной группы"""
        if group_name not in self.code_vectorizers or group_name not in self.code_models:
            return []
        
        # Векторизация для конкретной группы
        code_vector = self.code_vectorizers[group_name].transform([cleaned_text])
        
        code_vector = code_vector.toarray()
        
        # Предсказание вероятностей кодов
        code_probs = self.code_models[group_name].predict_proba(code_vector)[0]
        
        # Топ-N наиболее вероятных кодов в группе
        top_code_indices = np.argsort(code_probs)[-top_n_codes:][::-1]
        
        code_predictions = []
        for code_idx in top_code_indices:
            if code_probs[code_idx] > 0.01:
                code_name = self.group_id_to_code[group_name].get(int(code_idx), "UNKNOWN")
                code_predictions.append({
                    'code': code_name,
                    'confidence': code_probs[code_idx]
                })
        
        return code_predictions
    
    def _clean_text(self, text):
        """Очистка текста для предсказания"""
        text = str(text).lower()
        text = re.sub(r'[^а-яё0-9\s\.]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def set_mappings(self, group_mappings, code_mappings, codes_by_group):
        """Установка маппингов из препроцессора"""
        self.group_mappings = group_mappings
        self.code_mappings = code_mappings
        self.codes_by_group = codes_by_group
        
        # Создаем обратные маппинги
        self.id_to_group = {v: k for k, v in group_mappings.items()}
        self.id_to_code = {v: k for k, v in code_mappings.items()}
        
        print(f"🔧 Загружены маппинги:")
        print(f"   Группы: {list(group_mappings.keys())}")
        print(f"   Всего кодов: {len(code_mappings)}")
        for group_name, codes in codes_by_group.items():
            print(f"   Группа {group_name}: {len(codes)} кодов")
    
    def save_model(self, model_path):
        """Сохранение обученной модели"""
        model_data = {
            'group_model': self.group_model,
            'group_vectorizer': self.group_vectorizer,
            'code_models': self.code_models,
            'code_vectorizers': self.code_vectorizers,
            'group_mappings': self.group_mappings,
            'code_mappings': self.code_mappings,
            'codes_by_group': self.codes_by_group,
            'id_to_group': self.id_to_group,
            'id_to_code': self.id_to_code,
            'group_code_mappings': self.group_code_mappings,
            'group_id_to_code': self.group_id_to_code
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"💾 Двухуровневая модель сохранена: {model_path}")
    
    def load_model(self, model_path, console=True):
        """Загрузка обученной модели"""
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.group_model = model_data['group_model']
        self.group_vectorizer = model_data['group_vectorizer']
        self.code_models = model_data['code_models']
        self.code_vectorizers = model_data['code_vectorizers']
        self.group_mappings = model_data['group_mappings']
        self.code_mappings = model_data['code_mappings']
        self.codes_by_group = model_data['codes_by_group']
        self.id_to_group = model_data['id_to_group']
        self.id_to_code = model_data['id_to_code']
        self.group_code_mappings = model_data.get('group_code_mappings', {})
        self.group_id_to_code = model_data.get('group_id_to_code', {})
        
        if console:
            print(f"🔧 Двухуровневая модель загружена.")
            print(f"   Групп: {len(self.group_mappings)}")
            print(f"   Кодов: {len(self.code_mappings)}")
            print(f"   Моделей кодов: {len(self.code_models)}")

def train_complete_model():
    """Полный процесс обучения двухуровневой модели"""
    from simple_data_preprocessor import SimpleDataPreprocessor
    
    # 1. Подготовка данных
    print("🔧 ПОДГОТОВКА ДАННЫХ...")
    processor = SimpleDataPreprocessor(
        min_samples_per_class=20,
        min_group_samples=200
        )
    
    if not processor.load_data('your_data.csv'):
        return None
    
    df_processed = processor.prepare_for_training()
    
    if len(df_processed) == 0:
        print("❌ Недостаточно данных для обучения")
        return None
    
    # 2. Обучение двухуровневой модели
    print("\n🎯 ОБУЧЕНИЕ ДВУХУРОВНЕВОЙ МОДЕЛИ...")
    classifier = TwoLevelClassifier()
    
    # Устанавливаем маппинги
    classifier.set_mappings(
        processor.group_to_id,
        processor.code_to_id,
        processor.codes_by_group
    )
    
    # Обучаем модель
    classifier.train(df_processed)
    
    # 3. Сохранение модели
    classifier.save_model('two_level_classifier.pkl')
    
    # 4. Тестирование
    print("\n🧪 ТЕСТИРОВАНИЕ МОДЕЛИ:")
    test_texts = [
        "не греет вода в стиральной машине",
        "не сливает воду, гудит",
        "течет снизу, есть лужа",
        "не включается, трещит при запуске",
        "шумит при отжиме, вибрирует"
    ]
    
    for text in test_texts:
        predictions = classifier.predict(text)
        print(f"\n📝 Текст: '{text}'")
        for i, pred in enumerate(predictions, 1):
            print(f"   {i}. Группа {pred['group']} -> {pred['code']} - уверенность: {pred['confidence_percent']}")
    
    return classifier

def use_trained_model(file_path):
    """Пример использования обученной двухуровневой модели"""
    classifier = TwoLevelClassifier()
    
    if not os.path.exists(file_path):
        print("❌ Модель не найдена. Сначала обучите модель.")
        return
    
    classifier.load_model(file_path)
    
    print("\n🚀 ИНТЕРАКТИВНЫЙ РЕЖИМ ДВУХУРОВНЕВОЙ МОДЕЛИ")
    print("Вводите описания неисправностей, а ИИ предложит коды")
    print("=" * 50)
    
    while True:
        print("\nВведите описание неисправности (или 'выход' для завершения):")
        user_input = input("> ")
        
        if user_input.lower() in ['выход', 'exit', 'quit']:
            break
        
        if user_input.strip():
            predictions = classifier.predict(user_input, top_n_codes=3)
            print(f"\n🔍 Результаты для: '{user_input}'")
            
            if not predictions:
                print("   ❌ Не удалось определить неисправность")
                continue
                
            for i, pred in enumerate(predictions, 1):
                print(f"   {i}. Группа {pred['group']} -> {pred['code']}")
                print(f"      Общая уверенность: {pred['confidence_percent']}")
                print(f"      (Группа: {pred['group_confidence']:.3f}, Код: {pred['code_confidence']:.3f})")

if __name__ == "__main__":
    # Обучаем модель
    classifier = train_complete_model()
    
    # Или используем уже обученную
    # use_trained_model()