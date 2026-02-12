import time
import random
import csv
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

class AvitoParser:
    def __init__(self, output_file='avito_data.csv'):
        self.output_file = output_file
        self.driver = None

    def setup_driver(self):
        """Настройка undetected-chromedriver с опциями для скрытности."""
        options = uc.ChromeOptions()
        # Отключаем лишнюю графику, но не headless
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Стратегия загрузки 'eager' - не ждать полной загрузки ресурсов
        options.page_load_strategy = 'eager'

        self.driver = uc.Chrome(options=options, version_main=144)
        self.driver.maximize_window()

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

    def save_to_csv(self, data):
        """Запись данных в CSV файл в режиме добавления."""
        with open(self.output_file, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(data)

    def parse_page(self, url):
        """Парсинг одной страницы."""
        print(f"Загружаю страницу: {url}")
        self.driver.get(url)
        self.random_sleep(3, 6)
        
        # Обработка капчи (ручная)
        if "captcha" in self.driver.title.lower() or "ipv4" in self.driver.title.lower():
            print("ОБНАРУЖЕНА КАПЧА! Решите её в браузере и нажмите Enter здесь.")
            input()
            self.random_sleep(2, 4)

        self.lazy_scroll()
        
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Находим блоки объявлений (селекторы могут меняться, нужно проверять актуальные)
        # Обычно это div с data-marker='item'
        items = soup.find_all('div', attrs={'data-marker': 'item'})
        print(f"Найдено объявлений: {len(items)}")

        for item in items:
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

                data = [title, price, link, description, location]
                self.save_to_csv(data)
                
            except Exception as e:
                print(f"Ошибка при парсинге элемента: {e}")
                continue

    def run(self, start_url, max_pages=1, append=False):
        """Основной цикл запуска."""
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
                print(f"--- Страница {page} ---")
                self.parse_page(current_url)
                
                # Поиск кнопки "Следующая страница"
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                next_btn = soup.find('a', attrs={'data-marker': 'pagination-button/nextPage'})
                
                if next_btn and next_btn.get('href'):
                    current_url = "https://www.avito.ru" + next_btn['href']
                else:
                    print("Следующая страница не найдена. Завершение.")
                    break
                    
        except Exception as e:
            print(f"Критическая ошибка: {e}")
        finally:
            if self.driver:
                self.driver.quit()
            print("Работа завершена.")

if __name__ == "__main__":
    # Пример использования
    url = input("Введите URL категории или поиска Avito: ").strip()
    pages = int(input("Сколько страниц спарсить? ").strip())
    
    parser = AvitoParser()
    parser.run(url, pages)
