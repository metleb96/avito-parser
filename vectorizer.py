import csv
import json
import logging
from sentence_transformers import SentenceTransformer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AvitoVectorizer:
    def __init__(self, input_file='cleaned_avito_data.csv', output_file='vectorized_data.json', model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        self.input_file = input_file
        self.output_file = output_file
        self.model_name = model_name
        self.model = None

    def load_model(self):
        """Загрузка легковесной модели для эмбеддингов."""
        logging.info(f"Загрузка модели {self.model_name}...")
        try:
            self.model = SentenceTransformer(self.model_name)
            logging.info("Модель успешно загружена.")
        except Exception as e:
            logging.error(f"Ошибка при загрузке модели: {e}")
            raise

    def process_data(self):
        """Чтение данных, генерация векторов и сохранение."""
        if not self.model:
            self.load_model()

        logging.info(f"Чтение данных из {self.input_file}...")
        data_to_vectorize = []
        raw_data = []

        try:
            with open(self.input_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    if 'semantic_text' in row and row['semantic_text'].strip():
                        data_to_vectorize.append(row['semantic_text'])
                        raw_data.append(row)
            
            logging.info(f"Найдено {len(data_to_vectorize)} записей для векторизации.")

            if not data_to_vectorize:
                logging.warning("Нет данных для обработки.")
                return

            # Генерация эмбеддингов (batch_size можно уменьшить для экономии памяти)
            logging.info("Генерация эмбеддингов (это может занять время)...")
            embeddings = self.model.encode(data_to_vectorize, batch_size=32, show_progress_bar=True)

            # Объединение данных с векторами
            structured_output = []
            for i, row in enumerate(raw_data):
                item = row.copy()
                # Конвертируем numpy array в список для JSON сериализации
                item['embedding'] = embeddings[i].tolist()
                structured_output.append(item)

            # Сохранение в JSON (лучше подходит для списков-векторов, чем CSV)
            logging.info(f"Сохранение результатов в {self.output_file}...")
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(structured_output, f, ensure_ascii=False, indent=2)

            logging.info("Векторизация завершена успешно!")

        except FileNotFoundError:
            logging.error(f"Файл {self.input_file} не найден. Сначала запустите processor.py.")
        except Exception as e:
            logging.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    vectorizer = AvitoVectorizer()
    vectorizer.process_data()
