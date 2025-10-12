# main.py
from simple_data_preprocessor import SimpleDataPreprocessor
from simple_classifier import train_complete_model, use_trained_model
from pathlib import Path
import os


def main():
    print("🤖 ИИ-ПОМОЩНИК ДЛЯ ОПРЕДЕЛЕНИЯ КОДОВ НЕИСПРАВНОСТЕЙ")
    print("🎯 ДВУХУРОВНЕВАЯ АРХИТЕКТУРА")
    print("=" * 50)

    BASE_DIR = Path(__file__).resolve().parent.parent
    file_path = os.path.join(BASE_DIR, 'ml_model', 'two_level_classifier.pkl')
    if not os.path.exists(file_path):
        print("Модель не найдена. Запускаем обучение...")
        classifier = train_complete_model()

        if classifier is None:
            print("❌ Обучение не удалось. Проверьте данные.")
            return
    else:
        print("✅ Обученная двухуровневая модель найдена.")

    # Запуск интерактивного режима
    print("\n🚀 ЗАПУСК ИНТЕРАКТИВНОГО РЕЖИМА")
    print("Вводите описания неисправностей, а ИИ предложит коды")
    print("=" * 50)

    use_trained_model(file_path)


if __name__ == "__main__":
    main()