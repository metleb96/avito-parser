import time
import random
import csv
import logging
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import os
from typing import Optional, List, Dict, Any

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AvitoParser:
    """Парсер для сбора данных с Avito.ru с использованием Selenium и BeautifulSoup."""
    
    def __init__(self, output_file: str = 'avito_data.csv'):
        """
        Инициализация парсера.
        
        Args:
            output_file: Путь к выходному CSV файлу
        """
        self.output_file = output_file
        self.driver = None
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Настройка дополнительного логирования для парсера."""
        self.logger = logging.getLogger(__name__)

    def setup_driver(self) -> None:
        """
        Настройка undetected-chromedriver с опциями для скрытности.
        Автоматически определяет версию Chrome вместо хардкода.
        """
        options = uc.ChromeOptions()
        # Отключаем лишнюю графику, но не headless
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Стратегия загрузки 'eager' - не ждать полной загрузки ресурсов
        options.page_load_strategy = 'eager'

        try:
            # Автоматическое определение версии Chrome (без хардкода version_main)
            self.driver = uc.Chrome(options=options)
            self.driver.maximize_window()
            logger.info("WebDriver успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации WebDriver: {e}")
            raise

    def random_sleep(self, min_seconds=2, max_seconds=5):
        """Случайная задержка для имитации поведения человека."""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def lazy_scroll(self):
        """Ленивый скроллинг страницы для подгрузки динамического контента."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Скроллим вниз на случайную величину
            scroll_step = random.randint(300, 600)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_step});")
            self.random_sleep(0.5, 1.5)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            # Если доскроллили до низа (или близко), выходим
            # В Avito часто есть кнопка "Показать еще", но для пагинации обычно достаточно просто проскроллить
            if new_height == last_height: 
                 break
            last_height = new_height
            
            # Дополнительное условие выхода, если страница очень длинная
            if self.driver.execute_script("return window.innerHeight + window.scrollY >= document.body.offsetHeight - 100"):
                break

    def save_to_csv(self, data: List[str]) -> bool:
        """
        Запись данных в CSV файл в режиме добавления.
        
        Args:
            data: Список данных для записи
            
        Returns:
            True если запись успешна, False иначе
        """
        try:
            with open(self.output_file, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(data)
            return True
        except Exception as e:
            logger.error(f"Ошибка при записи в CSV: {e}")
            return False

    def parse_page(self, url: str) -> int:
        """
        Парсинг одной страницы.
        
        Args:
            url: URL страницы для парсинга
            
        Returns:
            Количество спарсенных объявлений
        """
        logger.info(f"Загружаю страницу: {url}")
        items_count = 0
        
        try:
            self.driver.get(url)
            self.random_sleep(3, 6)
            
            # Обработка капчи (ручная)
            if "captcha" in self.driver.title.lower() or "ipv4" in self.driver.title.lower():
                logger.warning("ОБНАРУЖЕНА КАПЧА! Решите её в браузере.")
                # В GUI режиме лучше использовать callback или событие
                input("Решите капчу и нажмите Enter здесь...")
                self.random_sleep(2, 4)

            self.lazy_scroll()
            
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Находим блоки объявлений (селекторы могут меняться, нужно проверять актуальные)
            # Обычно это div с data-marker='item'
            items = soup.find_all('div', attrs={'data-marker': 'item'})
            logger.info(f"Найдено объявлений: {len(items)}")

            for item in items:
                parsed_data = self._parse_item(item)
                if parsed_data:
                    if self.save_to_csv(parsed_data):
                        items_count += 1
                        
        except TimeoutException:
            logger.error(f"Timeout при загрузке страницы: {url}")
        except WebDriverException as e:
            logger.error(f"WebDriver ошибка при парсинге страницы: {e}")
        except Exception as e:
            logger.error(f"Критическая ошибка при парсинге страницы: {e}")
        
        return items_count
    
    def _parse_item(self, item) -> Optional[List[str]]:
        """
        Парсинг одного объявления.
        
        Args:
            item: BeautifulSoup элемент объявления
            
        Returns:
            Список данных [title, price, link, description, location] или None при ошибке
        """
        try:
            # Title
            title_tag = item.find('h3', attrs={'itemprop': 'name'})
            if not title_tag:
                title_tag = item.find('a', attrs={'data-marker': 'item-title'})
            title = title_tag.text.strip() if title_tag else "Нет названия"
            
            # Link
            link_tag = item.find('a', attrs={'itemprop': 'url'})
            if not link_tag:
                 link_tag = item.find('a', attrs={'data-marker': 'item-title'})
            link = "https://www.avito.ru" + link_tag['href'] if link_tag else "Нет ссылки"
            
            # Price
            price_tag = item.find('meta', attrs={'itemprop': 'price'})
            if price_tag:
                 price = price_tag.get('content')
            else:
                price_text_tag = item.find('p', attrs={'data-marker': 'item-price'})
                if not price_text_tag:
                    price_text_tag = item.find('span', attrs={'data-marker': 'item-price'})
                price = price_text_tag.text.strip().replace('\xa0', '').replace('₽', '') if price_text_tag else "0"

            # Description
            desc_tag = item.find('div', attrs={'class': lambda x: x and 'item-description' in x}) 
            if not desc_tag:
                desc_tag = item.find('meta', attrs={'itemprop': 'description'})
                if desc_tag:
                    description = desc_tag.get('content')
                else:
                    description = ""
            else:
                description = desc_tag.text.strip()
            
            # Location
            loc_tag = item.find('div', attrs={'data-marker': 'item-line'}) 
            if not loc_tag:
                # Try to find any text block that looks like location (usually near the bottom)
               loc_tag = item.find('div', attrs={'class': lambda x: x and 'geo-root' in x})
            location = loc_tag.text.strip() if loc_tag else "Нет локации"

            return [title, price, link, description, location]
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге элемента: {e}")
            return None

    def run(self, start_url: str, max_pages: int = 1, append: bool = False) -> Dict[str, Any]:
        """
        Основной цикл запуска парсинга.
        
        Args:
            start_url: Начальный URL для парсинга
            max_pages: Максимальное количество страниц для парсинга
            append: Режим добавления в существующий файл
            
        Returns:
            Словарь с результатами: {'success': bool, 'pages_parsed': int, 'items_count': int}
        """
        result = {'success': False, 'pages_parsed': 0, 'items_count': 0}
        
        try:
            self.setup_driver()
            
            # Инициализация CSV заголовков
            mode = 'a' if append else 'w'
            # Если файл не существует или мы перезаписываем, пишем заголовки
            write_headers = not append or not os.path.exists(self.output_file)

            if write_headers:
                 with open(self.output_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(['Название', 'Цена', 'Ссылка', 'Описание', 'Локация'])
            elif not os.path.exists(self.output_file):
                 # Fallback if append=True but file missing (should be covered above, but safe logic)
                 with open(self.output_file, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(['Название', 'Цена', 'Ссылка', 'Описание', 'Локация'])


            current_url = start_url
            for page in range(1, max_pages + 1):
                logger.info(f"--- Страница {page} ---")
                items_on_page = self.parse_page(current_url)
                result['items_count'] += items_on_page
                result['pages_parsed'] = page
                
                # Поиск кнопки "Следующая страница"
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                next_btn = soup.find('a', attrs={'data-marker': 'pagination-button/nextPage'})
                
                if next_btn and next_btn.get('href'):
                    current_url = "https://www.avito.ru" + next_btn['href']
                else:
                    logger.info("Следующая страница не найдена. Завершение.")
                    break
                    
            result['success'] = True
            logger.info(f"Парсинг завершен. Обработано страниц: {result['pages_parsed']}, Всего объявлений: {result['items_count']}")
            
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            result['success'] = False
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver закрыт")
            
        return result

if __name__ == "__main__":
    # Пример использования с обработкой ошибок
    try:
        url = input("Введите URL категории или поиска Avito: ").strip()
        if not url:
            logger.error("URL не может быть пустым")
            exit(1)
            
        pages_input = input("Сколько страниц спарсить? ").strip()
        try:
            pages = int(pages_input)
            if pages < 1:
                logger.error("Количество страниц должно быть больше 0")
                exit(1)
        except ValueError:
            logger.error("Некорректное количество страниц")
            exit(1)
        
        parser = AvitoParser()
        result = parser.run(url, pages)
        
        if result['success']:
            logger.info(f"Успешно завершено! Страниц: {result['pages_parsed']}, Объявлений: {result['items_count']}")
        else:
            logger.error("Парсинг завершился с ошибками")
            
    except KeyboardInterrupt:
        logger.info("Операция прервана пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
