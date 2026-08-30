import csv
import json
import logging
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AvitoVectorizer:
    """Класс для векторизации данных Avito с использованием Sentence Transformers."""
    
    def __init__(
        self, 
        input_file: str = 'cleaned_avito_data.csv', 
        output_file: str = 'vectorized_data.json', 
        model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'
    ):
        """
        Инициализация векторизатора.
        
        Args:
            input_file: Путь к входному CSV файлу с очищенными данными
            output_file: Путь к выходному JSON файлу с векторами
            model_name: Название модели для генерации эмбеддингов
        """
        self.input_file = input_file
        self.output_file = output_file
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None

    def load_model(self) -> None:
        """Загрузка легковесной модели для эмбеддингов."""
        logger.info(f"Загрузка модели {self.model_name}...")
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info("Модель успешно загружена.")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            raise

    def process_data(self) -> Dict[str, any]:
        """
        Чтение данных, генерация векторов и сохранение.
        
        Returns:
            Словарь с результатами: {'success': bool, 'items_vectorized': int}
        """
        result = {'success': False, 'items_vectorized': 0}
        
        if not self.model:
            self.load_model()

        logger.info(f"Чтение данных из {self.input_file}...")
        data_to_vectorize: List[str] = []
        raw_data: List[Dict] = []

        try:
            with open(self.input_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    if 'semantic_text' in row and row['semantic_text'].strip():
                        data_to_vectorize.append(row['semantic_text'])
                        raw_data.append(row)
            
            logger.info(f"Найдено {len(data_to_vectorize)} записей для векторизации.")

            if not data_to_vectorize:
                logger.warning("Нет данных для обработки.")
                return result

            # Генерация эмбеддингов (batch_size можно уменьшить для экономии памяти)
            logger.info("Генерация эмбеддингов (это может занять время)...")
            embeddings = self.model.encode(data_to_vectorize, batch_size=32, show_progress_bar=True)

            # Объединение данных с векторами
            structured_output = []
            for i, row in enumerate(raw_data):
                item = row.copy()
                # Конвертируем numpy array в список для JSON сериализации
                item['embedding'] = embeddings[i].tolist()
                structured_output.append(item)

            # Сохранение в JSON (лучше подходит для списков-векторов, чем CSV)
            logger.info(f"Сохранение результатов в {self.output_file}...")
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(structured_output, f, ensure_ascii=False, indent=2)

            result['success'] = True
            result['items_vectorized'] = len(structured_output)
            logger.info(f"Векторизация завершена успешно! Обработано {len(structured_output)} элементов.")

        except FileNotFoundError:
            logger.error(f"Файл {self.input_file} не найден. Сначала запустите processor.py.")
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
        
        return result

if __name__ == "__main__":
    vectorizer = AvitoVectorizer()
    vectorizer.process_data()
