# Avito Parser & AI Search

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 📖 Описание
Проект для парсинга объявлений с Avito, их очистки, векторизации и умного поиска на основе семантической близости (используя Sentence Transformers). Включает графический интерфейс (GUI) на CustomTkinter с поддержкой остановки операций, валидации URL, экспорта данных и фильтрации результатов.

## ✨ Возможности

### 🔍 Парсинг данных
- Сбор данных с Avito: Название, Цена, Ссылка, Описание, Локация
- Поддержка "ленивого" скроллинга для загрузки динамического контента
- Обработка капчи через GUI (ручной ввод при появлении)
- Автоматическое определение версии Chrome (без хардкода)
- Graceful degradation при ошибках парсинга отдельных элементов
- Промежуточное автосохранение данных во время сбора

### 🧹 Обработка и векторизация
- Очистка текста от мусора, эмодзи и HTML-тегов
- Нормализация данных
- Генерация векторных представлений (эмбеддингов) описаний товаров
- Кэширование модели для ускорения повторных запусков
- Batch processing для больших датасетов
- Прогресс-бары для длительных операций

### 🎯 Умный поиск
- Семантический поиск на естественном языке
- Пример: "игровой пк для киберпанка" найдет мощные ПК, даже если в заголовке нет этих слов
- Фильтрация результатов по цене, локации и дате публикации
- Пагинация результатов (по 10-20 элементов на странице)
- История последних поисковых запросов

### 🖥️ Графический интерфейс (GUI)
- Современный интерфейс на CustomTkinter
- Кнопка **Stop** для отмены долгих операций
- Валидация URL перед запуском парсинга
- Thread-safe обновления интерфейса
- Визуальные прогресс-бары для всех длительных задач
- Экспорт данных в CSV, Excel (.xlsx) и JSON
- Просмотр собранных данных с возможностью фильтрации

## 🚀 Установка

### Вариант 1: Классическая установка

1. Клонируйте репозиторий:
    ```bash
    git clone https://github.com/ваш-аккаунт/avito-parser.git
    cd avito-parser
    ```

2. Создайте виртуальное окружение (рекомендуется):
    ```bash
    # Linux/Mac
    python3 -m venv venv
    source venv/bin/activate
    
    # Windows
    python -m venv venv
    venv\Scripts\activate
    ```

3. Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```

4. Настройте конфигурацию:
    ```bash
    # Скопируйте пример конфигурации
    cp config.ini.example config.ini
    
    # При необходимости настройте .env для чувствительных данных
    cp .env.example .env
    # Отредактируйте .env и добавьте ваш HuggingFace токен (если нужен)
    ```

### Вариант 2: Docker (рекомендуется для production)

```bash
# Сборка образа
docker build -t avito-parser .

# Запуск с GUI (требуется X11)
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v $(pwd)/data:/app/data \
  avito-parser

# Запуск в headless режиме
docker run -it --rm \
  -v $(pwd)/data:/app/data \
  avito-parser python main.py --headless --url "https://www.avito.ru/..."
```

## ⚙️ Конфигурация

### config.ini
Основной файл конфигурации проекта:
```ini
[parser]
max_pages = 5
scroll_delay = 2.0
timeout = 30
headless = false

[processor]
model_name = sentence-transformers/rubert-base-cased
batch_size = 32
cache_model = true

[gui]
theme = dark
language = ru
results_per_page = 20
```

### .env (опционально)
Для хранения чувствительных данных:
```env
HF_TOKEN=your_huggingface_token_here
PROXY_URL=http://user:pass@proxy:port
```

## 📖 Использование

### Запуск GUI
```bash
python gui.py
```
Или используйте `start.bat` для быстрого запуска в Windows.

### Запуск в headless режиме (CLI)
```bash
python main.py --url "https://www.avito.ru/kompyutery_i_noutbuki" --pages 3 --output data/my_ads.csv
```

### Вкладки GUI

#### 1. 📥 Парсер
- Введите URL категории Avito (валидация выполняется автоматически)
- Укажите количество страниц для парсинга
- Нажмите **Start** для начала сбора данных
- Кнопка **Stop** позволяет прервать процесс в любой момент
- Данные автоматически сохраняются в процессе парсинга

#### 2. 🧹 Обработка
- **Очистка данных**: Удаление мусора, нормализация текста
- **Векторизация**: Создание эмбеддингов для семантического поиска
- Прогресс-бары отображают статус выполнения
- Возможность остановить операцию кнопкой **Stop**

#### 3. 🔍 Поиск
- Введите поисковый запрос на естественном языке
- Используйте фильтры:
  - Диапазон цен (от/до)
  - Локация (город, район)
  - Дата публикации
- Результаты отображаются с пагинацией
- Экспорт результатов в CSV/Excel/JSON

#### 4. 📊 Данные
- Просмотр всех собранных CSV файлов
- Фильтрация и сортировка по колонкам
- Предпросмотр данных перед экспортом

#### 5. 📜 История
- История последних поисковых запросов
- Быстрый повтор предыдущих поисков
- Статистика по собраным данным

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest

# Запуск с покрытием кода
pytest --cov=.

# Запуск конкретных тестов
pytest tests/test_parser.py -v
```

### Mock данные для тестирования
Проект включает набор mock данных для тестирования без реального парсинга:
```bash
python tests/generate_mock_data.py
```

## 📁 Структура проекта

```
avito-parser/
├── gui.py                 # Графический интерфейс
├── main.py                # Основной скрипт парсинга
├── processor.py           # Обработка и очистка данных
├── vectorizer.py          # Векторизация текстов
├── config.ini             # Файл конфигурации
├── .env.example           # Пример файла окружения
├── requirements.txt       # Зависимости Python
├── Dockerfile            # Docker образ
├── start.bat             # Скрипт запуска для Windows
├── tests/
│   ├── test_parser.py    # Тесты парсера
│   ├── test_processor.py # Тесты обработчика
│   ├── test_search.py    # Тесты поиска
│   └── mock_data/        # Mock данные для тестов
└── data/                  # Директория для сохранённых данных
```

## 🔧 Дополнительные возможности

### Proxy поддержка
Для обхода блокировок можно использовать proxy:
```bash
# В .env файле укажите:
PROXY_URL=http://user:pass@proxy-server:port

# Или передайте через CLI:
python main.py --proxy http://user:pass@proxy:port
```

### Headless режим
Для работы на серверах без GUI:
```bash
python main.py --headless --url "https://..."
```

### Мультиязычность
Интерфейс поддерживает русский и английский языки:
```ini
[gui]
language = en  # или ru
```

## ⚠️ Важно

Этот проект предназначен **только для образовательных целей**. Автоматический сбор данных может нарушать [правила использования Avito](https://www.avito.ru/info/terms). 

- Используйте разумные задержки между запросами
- Не собирайте данные в промышленных масштабах
- Уважайте robots.txt сайта
- Автор не несет ответственности за возможные блокировки аккаунта

## 🤝 Вклад в проект

1. Fork репозиторий
2. Создайте ветку (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в ветку (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

### Pre-commit хуки
Перед коммитом рекомендуется установить pre-commit хуки:
```bash
pip install pre-commit
pre-commit install
```

## 📄 Лицензия

MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 🙏 Благодарности

- [Avito](https://www.avito.ru) - площадка для объявлений
- [Hugging Face](https://huggingface.co) - модели для векторизации
- [CustomTkinter](https://customtkinter.tomschimansky.com) - современный GUI
- [Selenium](https://www.selenium.dev) - автоматизация браузера
- [Undetected Chromedriver](https://pypi.org/project/undetected-chromedriver/) - обход детекции ботов

## 📞 Контакты

Ваше Имя - [@yourtwitter](https://twitter.com/yourtwitter) - email@example.com

Ссылка на проект: [https://github.com/yourusername/avito-parser](https://github.com/yourusername/avito-parser)
