# your_app/ml_model.py
import os
from django.conf import settings
from .simple_classifier import TwoLevelClassifier


class MLModelLoader:
    _classifier = None

    @classmethod
    def get_classifier(cls):
        if cls._classifier is None:
            cls._classifier = TwoLevelClassifier()
            model_path = os.path.join(settings.ML_MODEL_PATH,
                                      'two_level_classifier.pkl')
            cls._classifier.load_model(model_path, False)
        return cls._classifier

