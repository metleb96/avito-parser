import csv
import re
import unicodedata
import logging
from typing import List, Dict

# Настройка логирования
logger = logging.getLogger(__name__)


class DataProcessor:
    """Класс для обработки и очистки данных Avito."""

    def __init__(self, input_file: str = 'avito_data.csv',
                 output_file: str = 'cleaned_avito_data.csv'):
        """
        Инициализация процессора данных.

        Args:
            input_file: Путь к входному CSV файлу
            output_file: Путь к выходному CSV файлу с очищенными данными
        """
        self.input_file = input_file
        self.output_file = output_file

    def clean_text(self, text: str) -> str:
        """
        Очищает текст от мусора:
        - Удаляет эмодзи и спецсимволы
        - Нормализует пробелы
        - Приводит к нижнему регистру (опционально, но полезно для поиска)

        Args:
            text: Текст для очистки

        Returns:
            Очищенный текст
        """
        if not text:
            return ""

        # 1. Нормализация Unicode (NFC)
        text = unicodedata.normalize('NFC', text)

        # 2. Удаление непечатных символов и эмодзи (оставляем только буквы, цифры, знаки препинания)
        # Этот regex оставляет кириллицу, латиницу, цифры и базовую пунктуацию
        text = re.sub(r'[^\w\s\.,!?;:()\-"\']', ' ', text)

        # 3. Замена множественных пробелов на один
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def create_semantic_text(self, row: List[str]) -> str:
        """
        Создает единый текстовый блок для векторизации.
        Формат: "Название: ... Цена: ... Локация: ... Описание: ..."

        Args:
            row: Список данных [title, price, link, description, location]

        Returns:
            Семантический текст для векторизации
        """
        # Индексы из main.py: 0-Title, 1-Price, 2-Link, 3-Description,
        # 4-Location
        title = self.clean_text(row[0])
        price = self.clean_text(row[1])
        # Ссылку (row[2]) usually не векторизуют, но сохраняют как метаданные
        description = self.clean_text(row[3])
        location = self.clean_text(row[4])

        # Формируем семантическое описание
        semantic_text = f"Товар: {title}. Цена: {price}. Место: {location}. Описание: {description}"
        return semantic_text

    def process(self) -> Dict[str, any]:
        """
        Обрабатывает данные из входного CSV файла.

        Returns:
            Словарь с результатами: {'success': bool, 'rows_processed': int}
        """
        result = {'success': False, 'rows_processed': 0}

        logger.info(
            f"Начинаю обработку {self.input_file} -> {self.output_file}")
        try:
            with open(self.input_file, 'r', encoding='utf-8-sig') as infile, \
                    open(self.output_file, 'w', newline='', encoding='utf-8-sig') as outfile:

                reader = csv.reader(infile, delimiter=';')
                writer = csv.writer(outfile, delimiter=';')

                # Читаем заголовки
                headers = next(reader, None)
                if headers:
                    # Добавляем новый столбец "semantic_text"
                    new_headers = headers + ['semantic_text']
                    writer.writerow(new_headers)

                count = 0
                for row in reader:
                    if not row:
                        continue

                    # Очищаем каждое поле
                    cleaned_row = [self.clean_text(cell) for cell in row]

                    # Генерируем поле для эмбеддинга
                    semantic_text = self.create_semantic_text(row)

                    # Записываем
                    writer.writerow(cleaned_row + [semantic_text])
                    count += 1

            result['success'] = True
            result['rows_processed'] = count
            logger.info(f"Готово! Обработано строк: {count}")

        except FileNotFoundError:
            logger.error(f"Ошибка: Файл {self.input_file} не найден.")
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")

        return result


if __name__ == "__main__":
    processor = DataProcessor()
    processor.process()
