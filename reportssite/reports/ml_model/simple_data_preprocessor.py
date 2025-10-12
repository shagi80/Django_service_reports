# simple_data_preprocessor.py
import pandas as pd
import re
import numpy as np
from collections import Counter
import pymorphy3
import nltk
import json

class SimpleDataPreprocessor:
    def __init__(self, min_samples_per_class=10, min_group_samples=50):
        self.min_samples_per_class = min_samples_per_class
        self.min_group_samples = min_group_samples
        self.morph = pymorphy3.MorphAnalyzer()
        self.stopwords = self._setup_nltk()
        
    def _setup_nltk(self):
        """Настройка NLTK с автоматической загрузкой необходимых данных"""
        try:
            from nltk.corpus import stopwords
            return set(stopwords.words('russian'))
        except LookupError:
            print("📥 NLTK данные не найдены. Скачиваем...")
            try:
                nltk.download('stopwords', quiet=True)
                from nltk.corpus import stopwords
                print("✅ NLTK стоп-слова успешно загружены")
                return set(stopwords.words('russian'))
            except:
                print("⚠️  Не удалось загрузить NLTK стоп-слова. Используем базовый список.")
                return self._get_basic_stopwords()
    
    def _get_basic_stopwords(self):
        """Базовый список русских стоп-слов"""
        basic_stopwords = [
            'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 
            'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 
            'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 
            'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 
            'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 
            'него', 'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 
            'потом', 'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть', 
            'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 'чтоб', 
            'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 
            'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем', 
            'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее', 
            'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при', 
            'наконец', 'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше', 
            'тот', 'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 
            'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой', 
            'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 
            'более', 'всегда', 'конечно', 'всю', 'между'
        ]
        return set(basic_stopwords)

    def load_data(self, file_path, separator='\t'):
        """Загрузка данных из CSV с указанием разделителя"""
        try:
            self.df = pd.read_csv(file_path, encoding='utf-8', sep=separator)
            print(f"✅ Загружено записей: {len(self.df)}")
            print(f"📊 Колонки: {self.df.columns.tolist()}")
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            return False
    
    def extract_group_from_code(self, code):
        """Извлечение группы из кода (первая буква) с улучшенной обработкой"""
        if pd.isna(code):
            return None
        
        code_str = str(code).strip()
        
        # Удаляем возможные пробелы в начале
        code_str = code_str.lstrip()
        
        if not code_str:
            return None
        
        # Берем первый символ и проверяем, что это буква
        first_char = code_str[0]
        
        if first_char.isalpha():
            return first_char.upper()  # Приводим к верхнему регистру
        else:
            # Если первый символ не буква, ищем первую букву
            for char in code_str:
                if char.isalpha():
                    return char.upper()
            return None  # Если букв нет вообще
    
    def analyze_data(self):
        """Анализ распределения данных"""
        print("\n" + "="*50)
        print("📋 АНАЛИЗ ДАННЫХ")
        print("="*50)
        
        # Проверка пропущенных значений
        missing = self.df.isnull().sum()
        print("\n🔍 Пропущенные значения:")
        for col, count in missing.items():
            if count > 0:
                print(f"   {col}: {count} ({count/len(self.df)*100:.1f}%)")
        
        # Анализ групп
        self.df['group'] = self.df['code'].apply(self.extract_group_from_code)
        group_stats = self.df['group'].value_counts()
        
        print(f"\n🎯 ГРУППЫ НЕИСПРАВНОСТЕЙ:")
        print(f"   Уникальных групп: {len(group_stats)}")
        for group, count in group_stats.items():
            codes_in_group = self.df[self.df['group'] == group]['code'].nunique()
            print(f"   Группа {group}: {count} примеров, {codes_in_group} кодов")
        
        # Анализ кодов внутри групп
        print(f"\n🔍 ДЕТАЛЬНЫЙ АНАЛИЗ КОДОВ:")
        code_stats = self.df['code'].value_counts()
        print(f"   Уникальных кодов: {len(code_stats)}")
        print(f"   Самый частый код: {code_stats.index[0]} ({code_stats.iloc[0]} раз)")
        
        # Проблемные классы
        small_classes = code_stats[code_stats < self.min_samples_per_class]
        print(f"   Кодов с <{self.min_samples_per_class} примерами: {len(small_classes)}")
    
    def clean_text(self, text):
        """Очистка текста описания неисправности"""
        if pd.isna(text):
            return ""
        
        text = str(text).lower()
        
        # Сохраняем ключевые глаголы и симптомы
        text = re.sub(r'[^а-яё0-9\s\.\,\!]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def lemmatize_text(self, text):
        """Лемматизация текста - приведение слов к нормальной форме"""
        words = text.split()
        lemmatized_words = []
        
        # Ключевые слова, которые нужно сохранить в исходной форме
        key_verbs = ['течет', 'греет', 'шумит', 'вибрирует', 'не включается', 
                    'не сливает', 'не вращается', 'протекает', 'не работает',
                    'морозит', 'гудит', 'трещит', 'не зажигается']
        
        for word in words:
            if len(word) < 2 or word in self.stopwords:
                continue
            
            # Сохраняем ключевые глаголы в исходной форме
            if word in key_verbs:
                lemmatized_words.append(word)
                continue
            
            # Приводим слово к нормальной форме
            try:
                parsed = self.morph.parse(word)[0]
                lemma = parsed.normal_form
                
                if len(lemma) >= 2:
                    lemmatized_words.append(lemma)
            except:
                lemmatized_words.append(word)
        
        return ' '.join(lemmatized_words)
    
    def debug_data_issues(self):
        """Детальная диагностика проблем с данными"""
        print("\n🔍 ДЕТАЛЬНАЯ ДИАГНОСТИКА ДАННЫХ:")
        
        # Анализ конкретных проблемных кодов
        problem_codes = ['B04', 'C01']
        
        for code in problem_codes:
            print(f"\n📋 АНАЛИЗ КОДА '{code}':")
            code_data = self.df[self.df['code'] == code]
            
            if len(code_data) == 0:
                # Пробуем найти похожие коды
                similar_codes = [c for c in self.df['code'].unique() if code in str(c)]
                print(f"   Код не найден! Похожие коды: {similar_codes}")
            else:
                print(f"   Найдено записей: {len(code_data)}")
                print(f"   Распределение по группам:")
                group_counts = code_data['group'].value_counts()
                for group, count in group_counts.items():
                    sample_text = code_data[code_data['group'] == group]['problem_description'].iloc[0]
                    print(f"      Группа {group}: {count} записей")
                    print(f"      Пример текста: {sample_text[:80]}...")
        
        # Проверяем уникальность кодов
        print(f"\n🎯 УНИКАЛЬНОСТЬ КОДОВ:")
        code_stats = self.df['code'].value_counts()
        duplicate_codes = code_stats[code_stats > 1].index.tolist()
        
        print(f"   Всего уникальных кодов: {len(code_stats)}")
        print(f"   Кодов с дубликатами: {len(duplicate_codes)}")
        
        # Анализ нескольких дублирующихся кодов
        for code in duplicate_codes[:5]:
            groups = self.df[self.df['code'] == code]['group'].unique()
            if len(groups) > 1:
                print(f"   ❌ Код '{code}' находится в группах: {list(groups)}")

    def prepare_for_training(self):
        """Подготовка данных для обучения модели"""
        print("\n" + "="*50)
        print("🎯 ПОДГОТОВКА ДЛЯ ОБУЧЕНИЯ")
        print("="*50)
        
        initial_count = len(self.df)
        
        # 1. Удаляем строки с пропущенными значениями
        self.df = self.df.dropna(subset=['problem_description', 'code'])
        print(f"📝 Удалено строк с пропусками: {initial_count - len(self.df)}")
        
        # 2. Извлекаем группы
        self.df['group'] = self.df['code'].apply(self.extract_group_from_code)
        self.df = self.df.dropna(subset=['group'])
        
        #
        self.debug_data_issues()

        # 3. Очищаем текст неисправностей
        self.df['problem_cleaned'] = self.df['problem_description'].apply(self.clean_text)
        
        # 4. Удаляем слишком короткие тексты
        self.df = self.df[self.df['problem_cleaned'].str.len() >= 10]
        print(f"📏 Удалено коротких текстов: {initial_count - len(self.df)}")
        
        # 5. Лемматизируем текст
        print("🔤 Лемматизация текстов...")
        self.df['problem_lemmatized'] = self.df['problem_cleaned'].apply(self.lemmatize_text)
        
        # 6. Обрабатываем маленькие классы и группы
        self._handle_small_groups_and_classes()
        
        # 7. Создаем числовые метки для групп и кодов
        self._create_mappings()
        
        print(f"\n✅ ФИНАЛЬНАЯ СТАТИСТИКА:")
        print(f"   Всего записей: {len(self.df)}")
        print(f"   Уникальных групп: {len(self.group_to_id)}")
        print(f"   Уникальных кодов: {len(self.code_to_id)}")
        
        # Показываем распределение по группам
        group_counts = self.df['group'].value_counts()
        print(f"\n📊 РАСПРЕДЕЛЕНИЕ ПО ГРУППАМ:")
        for group, count in group_counts.items():
            codes_count = self.df[self.df['group'] == group]['code'].nunique()
            print(f"   Группа {group}: {count} примеров, {codes_count} кодов")
        
        return self.df
    
    def _handle_small_groups_and_classes(self):
        """Обработка групп и классов с малым количеством примеров"""
        # Удаляем коды с малым количеством примеров
        code_counts = self.df['code'].value_counts()
        small_codes = code_counts[code_counts < self.min_samples_per_class].index
        
        if len(small_codes) > 0:
            print(f"🗑️  Удаляем коды с <{self.min_samples_per_class} примерами: {len(small_codes)} кодов")
            initial_count = len(self.df)
            self.df = self.df[~self.df['code'].isin(small_codes)]
            print(f"   Удалено записей: {initial_count - len(self.df)}")
        
        # Удаляем группы с малым количеством примеров
        group_counts = self.df['group'].value_counts()
        small_groups = group_counts[group_counts < self.min_group_samples].index
        
        if len(small_groups) > 0:
            print(f"🗑️  Удаляем группы с <{self.min_group_samples} примерами: {len(small_groups)} групп")
            initial_count = len(self.df)
            self.df = self.df[~self.df['group'].isin(small_groups)]
            print(f"   Удалено записей: {initial_count - len(self.df)}")
    
    def _create_mappings(self):
        """Создание маппингов для групп и кодов"""
        # Маппинги для групп
        unique_groups = sorted(self.df['group'].unique())
        self.group_to_id = {group: idx for idx, group in enumerate(unique_groups)}
        self.id_to_group = {idx: group for group, idx in self.group_to_id.items()}
        self.df['group_id'] = self.df['group'].map(self.group_to_id)
        
        # Маппинги для кодов (внутри групп)
        self.code_to_id = {}
        self.id_to_code = {}
        
        for group in unique_groups:
            group_codes = sorted(self.df[self.df['group'] == group]['code'].unique())
            for code in group_codes:
                code_id = len(self.code_to_id)
                self.code_to_id[code] = code_id
                self.id_to_code[code_id] = code
        
        self.df['code_id'] = self.df['code'].map(self.code_to_id)
        
        # Создаем mapping кодов по группам
        self.codes_by_group = {}
        for group in unique_groups:
            self.codes_by_group[group] = list(self.df[self.df['group'] == group]['code'].unique())
    
    def get_data_by_group(self, group):
        """Получение данных для конкретной группы"""
        return self.df[self.df['group'] == group]
    
    def save_processed_data(self, output_path):
        """Сохранение обработанных данных"""
        self.df.to_csv(output_path, index=False, encoding='utf-8')
        
        # Сохраняем метаданные для модели
        metadata = {
            'group_mappings': self.group_to_id,
            'id_to_group': self.id_to_group,
            'code_mappings': self.code_to_id,
            'id_to_code': self.id_to_code,
            'codes_by_group': self.codes_by_group,
            'preprocessing_info': {
                'total_samples': len(self.df),
                'total_groups': len(self.group_to_id),
                'total_codes': len(self.code_to_id),
                'min_samples_per_class': self.min_samples_per_class,
                'min_group_samples': self.min_group_samples
            }
        }
        
        metadata_path = output_path.replace('.csv', '_metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Данные сохранены: {output_path}")
        print(f"📋 Метаданные сохранены: {metadata_path}")
    
    def show_samples(self, n=3):
        """Показать примеры обработанных данных"""
        print(f"\n📄 ПРИМЕРЫ ОБРАБОТАННЫХ ДАННЫХ (первые {n}):")
        for i in range(min(n, len(self.df))):
            row = self.df.iloc[i]
            print(f"\nПример {i+1}:")
            print(f"   Исходный текст: {row['problem_description'][:80]}...")
            print(f"   Очищенный текст: {row['problem_cleaned'][:80]}...")
            print(f"   Лемматизированный: {row['problem_lemmatized'][:80]}...")
            print(f"   Группа: {row['group']}")
            print(f"   Код: {row['code']}")

# Использование
def main():
    processor = SimpleDataPreprocessor(min_samples_per_class=10, min_group_samples=50)
    
    if processor.load_data('your_data.csv'):
        processor.analyze_data()
        df_processed = processor.prepare_for_training()
        processor.show_samples(3)
        processor.save_processed_data('processed_data.csv')

if __name__ == "__main__":
    main()