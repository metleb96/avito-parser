import tkinter as tk
import customtkinter as ctk
import threading
import sys
import io
import os
import datetime
import glob
import re
import json
import csv
from tkinter import messagebox
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

# Импортируем наши модули
from main import AvitoParser
from processor import DataProcessor
from vectorizer import AvitoVectorizer
from sentence_transformers import SentenceTransformer, util

# Настройка темы
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class RedirectText(io.StringIO):
    """Класс для перенаправления stdout в текстовый виджет."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.configure(state="normal")
        self.text_widget.insert("end", string)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def flush(self):
        pass

class AvitoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Avito Parser & AI Search")
        self.geometry("900x700")

        # Переменные для управления потоками
        self.parsing_thread: Optional[threading.Thread] = None
        self.processor_thread: Optional[threading.Thread] = None
        self.vectorizer_thread: Optional[threading.Thread] = None
        self.stop_parsing = False

        # Создаем вкладки
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self.tab_parser = self.tabview.add("Парсер (Parser)")
        self.tab_process = self.tabview.add("Обработка (Process)")
        self.tab_search = self.tabview.add("Поиск (Search)")
        self.tab_view = self.tabview.add("Данные (Data)")

        self._setup_parser_tab()
        self._setup_process_tab()
        self._setup_search_tab()
        self._setup_view_tab()

        # Для поиска (загружаем модель лениво при первом использовании)
        self.model = None
        self.vector_data = None

    def _create_context_menu(self, widget):
        """Создает контекстное меню (Копировать/Вставить) для виджета."""
        menu = tk.Menu(self, tearoff=0)

        def do_copy():
            try:
                selected_text = widget.selection_get()
                self.clipboard_clear()
                self.clipboard_append(selected_text)
            except:
                pass

        def do_paste():
            try:
                text = self.clipboard_get()
                widget.insert(tk.INSERT, text)
            except:
                pass
        
        def do_cut():
            try:
                do_copy()
                widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
            except:
                pass

        menu.add_command(label="Копировать (Copy)", command=do_copy)
        menu.add_command(label="Вставить (Paste)", command=do_paste)
        menu.add_command(label="Вырезать (Cut)", command=do_cut)

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)

    def _setup_parser_tab(self):
        """Вкладка Парсинга с валидацией URL и кнопкой Stop"""
        frame = self.tab_parser
        
        # Инпут URL
        ctk.CTkLabel(frame, text="URL Категории (Avito):").pack(pady=(10, 5))
        self.url_entry = ctk.CTkEntry(frame, width=600, placeholder_text="https://www.avito.ru/...")
        self.url_entry.pack(pady=5)
        self._create_context_menu(self.url_entry)

        # Кнопка валидации URL
        self.validate_btn = ctk.CTkButton(frame, text="✓ Проверить URL", command=self.validate_url, 
                                          fg_color="#2196F3", width=150)
        self.validate_btn.pack(pady=5)
        self.url_status_label = ctk.CTkLabel(frame, text="", text_color="gray", font=("Arial", 10))
        self.url_status_label.pack()

        # Инпут Pages
        ctk.CTkLabel(frame, text="Количество страниц:").pack(pady=(10, 5))
        self.pages_slider = ctk.CTkSlider(frame, from_=1, to=10, number_of_steps=9, width=400)
        self.pages_slider.pack(pady=5)
        self.pages_label = ctk.CTkLabel(frame, text="1")
        self.pages_label.pack()
        self.pages_slider.configure(command=lambda val: self.pages_label.configure(text=str(int(val))))
        
        # Режим хранения
        ctk.CTkLabel(frame, text="Режим записи данных:").pack(pady=(10, 5))
        self.storage_mode = ctk.CTkSegmentedButton(frame, values=["Перезаписать", "Дополнить", "Новый файл"])
        self.storage_mode.set("Перезаписать")
        self.storage_mode.pack(pady=5)

        # Кнопки управления
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=20)
        
        self.start_btn = ctk.CTkButton(btn_frame, text="Запустить парсинг", command=self.start_parsing, fg_color="green")
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = ctk.CTkButton(btn_frame, text="⏹ Остановить", command=self.stop_parsing_task, 
                                      fg_color="#f44336", state="disabled")
        self.stop_btn.pack(side="left", padx=10)

        # Прогресс бар
        self.progress_bar = ctk.CTkProgressBar(frame, width=400)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(frame, text="Готов к работе", text_color="gray")
        self.progress_label.pack()

        # Консоль
        ctk.CTkLabel(frame, text="Лог работы:").pack(pady=(10, 5), anchor="w")
        self.log_box = ctk.CTkTextbox(frame, height=300)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_box.configure(state="disabled")

    def _setup_process_tab(self):
        """Вкладка Обработки данных с прогресс-барами"""
        frame = self.tab_process
        
        ctk.CTkLabel(frame, text="Этап 1: Очистка данных", font=("Arial", 16, "bold")).pack(pady=20)
        
        proc_btn_frame = ctk.CTkFrame(frame)
        proc_btn_frame.pack(pady=10)
        ctk.CTkButton(proc_btn_frame, text="Запустить очистку (Processor)", command=self.run_processor).pack(side="left", padx=10)
        self.stop_processor_btn = ctk.CTkButton(proc_btn_frame, text="⏹ Стоп", command=self.stop_processor_task, 
                                                 fg_color="#f44336", state="disabled")
        self.stop_processor_btn.pack(side="left", padx=10)
        
        self.clean_status = ctk.CTkLabel(frame, text="Статус: Ожидание", text_color="gray")
        self.clean_status.pack()
        self.clean_progress = ctk.CTkProgressBar(frame, width=400)
        self.clean_progress.pack(pady=5)
        self.clean_progress.set(0)

        ctk.CTkLabel(frame, text="Этап 2: Векторизация (AI)", font=("Arial", 16, "bold")).pack(pady=20)
        
        vec_btn_frame = ctk.CTkFrame(frame)
        vec_btn_frame.pack(pady=10)
        ctk.CTkButton(vec_btn_frame, text="Создать эмбеддинги (Vectorizer)", command=self.run_vectorizer, fg_color="#5500aa").pack(side="left", padx=10)
        self.stop_vectorizer_btn = ctk.CTkButton(vec_btn_frame, text="⏹ Стоп", command=self.stop_vectorizer_task,
                                                  fg_color="#f44336", state="disabled")
        self.stop_vectorizer_btn.pack(side="left", padx=10)
        
        self.vector_status = ctk.CTkLabel(frame, text="Статус: Ожидание", text_color="gray")
        self.vector_status.pack()
        self.vector_progress = ctk.CTkProgressBar(frame, width=400)
        self.vector_progress.pack(pady=5)
        self.vector_progress.set(0)

        self.process_log = ctk.CTkTextbox(frame, height=200)
        self.process_log.pack(fill="both", expand=True, padx=20, pady=20)
        self.process_log.configure(state="disabled")

    def _setup_search_tab(self):
        """Вкладка Поиска с фильтрами и экспортом"""
        frame = self.tab_search

        ctk.CTkLabel(frame, text="Умный поиск по базе", font=("Arial", 18)).pack(pady=10)
        
        # Поле поиска и фильтры
        search_frame = ctk.CTkFrame(frame)
        search_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(search_frame, text="Запрос:").grid(row=0, column=0, padx=5, pady=5)
        self.query_entry = ctk.CTkEntry(search_frame, width=400, placeholder_text="Например: игровой пк для киберпанка")
        self.query_entry.grid(row=0, column=1, padx=5, pady=5)
        self._create_context_menu(self.query_entry)
        
        # Фильтры
        ctk.CTkLabel(search_frame, text="Макс. цена:").grid(row=0, column=2, padx=5, pady=5)
        self.max_price_entry = ctk.CTkEntry(search_frame, width=100, placeholder_text="₽")
        self.max_price_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ctk.CTkLabel(search_frame, text="Город:").grid(row=0, column=4, padx=5, pady=5)
        self.city_entry = ctk.CTkEntry(search_frame, width=150, placeholder_text="Москва")
        self.city_entry.grid(row=0, column=5, padx=5, pady=5)
        
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="🔍 Найти", command=self.run_search).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="📥 Экспорт результатов", command=self.export_results, fg_color="#4CAF50").pack(side="left", padx=10)

        # Результаты с пагинацией
        self.results_count_label = ctk.CTkLabel(frame, text="Найдено: 0", text_color="gray")
        self.results_count_label.pack(pady=5)
        
        self.results_frame = ctk.CTkScrollableFrame(frame, width=800, height=500)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Хранилище результатов для экспорта
        self.current_search_results = []

    def _setup_view_tab(self):
        """Вкладка Просмотра данных с экспортом"""
        frame = self.tab_view
        
        # Управление
        ctrl_frame = ctk.CTkFrame(frame)
        ctrl_frame.pack(fill="x", padx=10, pady=10)
        
        self.view_file_var = ctk.StringVar(value="")
        self.file_combo = ctk.CTkComboBox(ctrl_frame, values=[], variable=self.view_file_var, width=300)
        self.file_combo.pack(side="left", padx=10)
        
        ctk.CTkButton(ctrl_frame, text="🔄 Обновить список", width=120, command=self.refresh_file_list).pack(side="left", padx=5)
        ctk.CTkButton(ctrl_frame, text="Загрузить (Топ 50)", command=self.load_table_data).pack(side="left", padx=10)
        ctk.CTkButton(ctrl_frame, text="📥 Экспорт в Excel", command=self.export_to_excel, fg_color="#2196F3").pack(side="left", padx=10)
        ctk.CTkButton(ctrl_frame, text="📄 Экспорт в JSON", command=self.export_to_json, fg_color="#FF9800").pack(side="left", padx=10)
        
        self.table_frame = ctk.CTkScrollableFrame(frame, width=850, height=500)
        self.table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Initial load
        self.refresh_file_list()

    def refresh_file_list(self):
        """Обновляет список CSV файлов в выпадающем меню."""
        files = glob.glob("*.csv")
        # Сортируем: сначала новые
        files.sort(key=os.path.getmtime, reverse=True)
        
        if files:
            self.file_combo.configure(values=files)
            self.view_file_var.set(files[0])
        else:
             self.file_combo.configure(values=["Нет CSV файлов"])
             self.view_file_var.set("Нет CSV файлов")

    # --- Logic ---

    def validate_url(self) -> None:
        """Валидация URL Avito с использованием regex и urlparse."""
        url = self.url_entry.get().strip()
        
        if not url:
            self.url_status_label.configure(text="❌ URL пуст", text_color="red")
            return
        
        # Проверка формата URL
        avito_pattern = r'^https?://(www\.)?avito\.ru/.*'
        if not re.match(avito_pattern, url, re.IGNORECASE):
            self.url_status_label.configure(text="❌ Неверный формат URL (должен быть avito.ru)", text_color="red")
            return
        
        # Дополнительная проверка через urlparse
        try:
            parsed = urlparse(url)
            if parsed.netloc not in ['avito.ru', 'www.avito.ru']:
                self.url_status_label.configure(text="❌ Домен должен быть avito.ru", text_color="red")
                return
        except Exception:
            self.url_status_label.configure(text="❌ Ошибка парсинга URL", text_color="red")
            return
        
        self.url_status_label.configure(text="✅ URL корректен", text_color="green")
        messagebox.showinfo("Проверка URL", "URL корректен и готов к парсингу!")

    def stop_parsing_task(self) -> None:
        """Остановка задачи парсинга."""
        self.stop_parsing = True
        self.progress_label.configure(text="Остановка...", text_color="orange")
        logger.info("Пользователь запросил остановку парсинга")

    def stop_processor_task(self) -> None:
        """Остановка задачи процессора."""
        self.stop_processor = True
        self.clean_status.configure(text="Статус: Остановка...", text_color="orange")

    def stop_vectorizer_task(self) -> None:
        """Остановка задачи векторизатора."""
        self.stop_vectorizer = True
        self.vector_status.configure(text="Статус: Остановка...", text_color="orange")

    def redirect_logging(self, widget):
         sys.stdout = RedirectText(widget)
         sys.stderr = RedirectText(widget)

    def reset_logging(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def load_table_data(self):
        filename = self.view_file_var.get()
        if not os.path.exists(filename):
             messagebox.showerror("Ошибка", f"Файл {filename} не найден!")
             return

        # Очистка
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=';')
                headers = next(reader, None)
                if not headers: return
                
                # Заголовки
                for col_idx, header in enumerate(headers):
                    ctk.CTkLabel(self.table_frame, text=header, text_color="yellow", font=("Arial", 12, "bold")).grid(row=0, column=col_idx, padx=5, pady=5, sticky="w")

                # Данные (первые 50 строк)
                for row_idx, row in enumerate(reader, start=1):
                    if row_idx > 50: break
                    for col_idx, cell in enumerate(row):
                        # Обрезаем длинный текст
                        display_text = (cell[:50] + '..') if len(cell) > 50 else cell
                        ctk.CTkEntry(self.table_frame, width=150 if col_idx != 3 else 300).grid(row=row_idx, column=col_idx, padx=2, pady=2)
                        # Используем Entry как лейбл, чтобы можно было копировать, но ставим текст через insert
                        # (в цикле grid быстрее создавать Entry сразу, но тут упрощенно)
                        # Точнее:
                        e = ctk.CTkEntry(self.table_frame, width=150 if col_idx != 3 else 300) # Описание пошире
                        e.insert(0, display_text)
                        e.configure(state="readonly")
                        e.grid(row=row_idx, column=col_idx, padx=2, pady=2, sticky="ew")
                        
        except Exception as e:
            messagebox.showerror("Ошибка чтения", str(e))

    def start_parsing(self) -> None:
        """Запуск парсинга с валидацией и обновлением прогресс-бара."""
        url = self.url_entry.get()
        
        # Валидация URL перед запуском
        if not url:
            messagebox.showerror("Ошибка", "Введите URL!")
            return
        
        avito_pattern = r'^https?://(www\.)?avito\.ru/.*'
        if not re.match(avito_pattern, url, re.IGNORECASE):
            messagebox.showerror("Ошибка", "Неверный формат URL! Должен быть вида https://www.avito.ru/...")
            return
        
        pages = int(self.pages_slider.get())
        mode = self.storage_mode.get()

        # Логика режимов
        filename = "avito_data.csv"
        append = False

        if mode == "Перезаписать":
            filename = "avito_data.csv"
            append = False
        elif mode == "Дополнить":
            filename = "avito_data.csv"
            append = True
        elif mode == "Новый файл":
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"avito_data_{timestamp}.csv"
            append = False

        # Сброс флага остановки
        self.stop_parsing = False
        
        # Обновление UI
        self.start_btn.configure(state="disabled", text="Работает...")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Инициализация...", text_color="blue")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        self.parsing_thread = threading.Thread(target=self._parsing_thread, args=(url, pages, filename, append), daemon=True)
        self.parsing_thread.start()

    def _parsing_thread(self, url: str, pages: int, filename: str, append: bool) -> None:
        """Поток выполнения парсинга с обновлением прогресса через after()."""
        self.redirect_logging(self.log_box)
        try:
            self.after(0, lambda: self.progress_label.configure(text=f"Страница 1 из {pages}", text_color="blue"))
            print(f"[GUI] Старт. Файл: {filename}, Режим: {'Append' if append else 'Overwrite'}")
            
            parser = AvitoParser(output_file=filename)
            
            # Модифицируем run для поддержки остановки (через проверку флага)
            total_items = 0
            for page in range(1, pages + 1):
                if self.stop_parsing:
                    print("\n[GUI] Парсинг остановлен пользователем")
                    break
                    
                self.after(0, lambda p=page: self.progress_bar.set(p / pages))
                self.after(0, lambda p=page: self.progress_label.configure(text=f"Страница {p} из {pages}", text_color="blue"))
                
                items_on_page = parser.parse_page(url if page == 1 else url)
                total_items += items_on_page
                
                # Переход на следующую страницу (упрощенно)
                if page < pages and not self.stop_parsing:
                    # Логика перехода будет в parser.run
                    pass
            
            print(f"\n[GUI] Парсинг завершен! Обработано страниц: {min(pages, page)}, Всего объявлений: {total_items}")
            self.after(0, lambda: self.progress_label.configure(text="✅ Завершено", text_color="green"))
            self.after(0, lambda: self.progress_bar.set(1.0))
            
        except Exception as e:
            print(f"\n[GUI] Ошибка: {e}")
            self.after(0, lambda: self.progress_label.configure(text="❌ Ошибка", text_color="red"))
        finally:
            self.reset_logging()
            self.after(0, lambda: self.start_btn.configure(state="normal", text="Запустить парсинг"))
            self.after(0, lambda: self.stop_btn.configure(state="disabled"))

    def run_processor(self) -> None:
        """Запуск процессора данных с прогресс-баром и кнопкой стоп."""
        self.redirect_logging(self.process_log)
        self.stop_processor = False
        self.clean_status.configure(text="Статус: В работе...", text_color="yellow")
        self.clean_progress.set(0)
        self.stop_processor_btn.configure(state="normal")
        
        def task() -> None:
            try:
                proc = DataProcessor()
                # Эмуляция прогресса (2 этапа)
                self.after(0, lambda: self.clean_progress.set(0.3))
                proc.process()
                self.after(0, lambda: self.clean_progress.set(1.0))
                self.after(0, lambda: self.clean_status.configure(text="Статус: Готово ✅", text_color="green"))
            except Exception as e:
                print(e)
                self.after(0, lambda: self.clean_status.configure(text="Статус: Ошибка ❌", text_color="red"))
            finally:
                self.reset_logging()
                self.after(0, lambda: self.stop_processor_btn.configure(state="disabled"))

        self.processor_thread = threading.Thread(target=task, daemon=True)
        self.processor_thread.start()

    def run_vectorizer(self) -> None:
        """Запуск векторизатора с прогресс-баром и кнопкой стоп."""
        self.redirect_logging(self.process_log)
        self.stop_vectorizer = False
        self.vector_status.configure(text="Статус: В работе...", text_color="yellow")
        self.vector_progress.set(0)
        self.stop_vectorizer_btn.configure(state="normal")
        
        def task() -> None:
            try:
                vec = AvitoVectorizer()
                # Эмуляция прогресса
                self.after(0, lambda: self.vector_progress.set(0.2))
                vec.process_data()
                self.after(0, lambda: self.vector_progress.set(1.0))
                self.after(0, lambda: self.vector_status.configure(text="Статус: Готово ✅", text_color="green"))
                # Reset loaded data so search tab reloads it
                self.vector_data = None 
            except Exception as e:
                print(e)
                self.after(0, lambda: self.vector_status.configure(text="Статус: Ошибка ❌", text_color="red"))
            finally:
                self.reset_logging()
                self.after(0, lambda: self.stop_vectorizer_btn.configure(state="disabled"))

        self.vectorizer_thread = threading.Thread(target=task, daemon=True)
        self.vectorizer_thread.start()

    def run_search(self) -> None:
        """Запуск поиска с фильтрами."""
        query = self.query_entry.get()
        if not query:
            messagebox.showwarning("Внимание", "Введите поисковый запрос!")
            return
        
        # Очистка результатов
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        self.current_search_results = []
        
        threading.Thread(target=self._search_thread, args=(query,), daemon=True).start()

    def _search_thread(self, query: str) -> None:
        """Поток выполнения поиска с применением фильтров."""
        try:
            # 1. Загрузка модели и данных (если еще нет)
            if self.model is None:
                # Используем более мощную многоязычную модель
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            
            if self.vector_data is None:
                if not os.path.exists('vectorized_data.json'):
                    self.after(0, lambda: self.results_frame.configure(label_text="Ошибка: Файл vectorized_data.json не найден"))
                    return
                with open('vectorized_data.json', 'r', encoding='utf-8') as f:
                    self.vector_data = json.load(f)

            # 2. Поиск
            query_embedding = self.model.encode(query, convert_to_tensor=True)
            
            # Собираем эмбеддинги из данных
            import torch
            corpus_embeddings = torch.tensor([item['embedding'] for item in self.vector_data])
            
            # Считаем косинусное сходство
            hits = util.semantic_search(query_embedding, corpus_embeddings, top_k=50)
            
            # Применяем фильтры
            filtered_hits = []
            max_price = self.max_price_entry.get().strip()
            city = self.city_entry.get().strip().lower()
            
            for hit in hits[0]:
                idx = hit['corpus_id']
                item = self.vector_data[idx]
                
                # Фильтр по цене
                if max_price:
                    try:
                        item_price = int(item.get('Цена', '0').replace('₽', '').replace(' ', ''))
                        if item_price > int(max_price):
                            continue
                    except (ValueError, AttributeError):
                        pass
                
                # Фильтр по городу
                if city:
                    item_location = item.get('Локация', item.get('Location', '')).lower()
                    if city not in item_location:
                        continue
                
                filtered_hits.append(hit)
            
            # Сохраняем результаты для экспорта
            self.current_search_results = [self.vector_data[h['corpus_id']] for h in filtered_hits]
            
            # Обновляем счетчик
            self.after(0, lambda: self.results_count_label.configure(text=f"Найдено: {len(filtered_hits)}"))
            
            # 3. GUI Update
            self.after(0, lambda: self._display_results(filtered_hits))

        except Exception as e:
            print(f"Search Error: {e}")
            self.after(0, lambda: self.results_frame.configure(label_text=f"Ошибка поиска: {e}"))

    def _display_results(self, hits: List[Dict]) -> None:
        """Отображение результатов поиска в GUI."""
        if not hits:
            ctk.CTkLabel(self.results_frame, text="Ничего не найдено").pack()
            return

        for hit in hits:
            idx = hit['corpus_id']
            score = hit['score']
            item = self.vector_data[idx]
            
            # Карточка товара
            card = ctk.CTkFrame(self.results_frame)
            card.pack(fill="x", pady=5, padx=5)
            
            title = item.get('Название', item.get('Title', 'No Title'))
            price = item.get('Цена', item.get('Price', '0'))
            location = item.get('Локация', item.get('Location', ''))
            link_url = item.get('Ссылка', item.get('Link', ''))

            ctk.CTkLabel(card, text=title, font=("Arial", 14, "bold"), anchor="w").pack(fill="x", padx=5, pady=2)
            ctk.CTkLabel(card, text=f"{price} | {location}", text_color="lightgray", anchor="w").pack(fill="x", padx=5)
            ctk.CTkLabel(card, text=f"Сходство: {score:.4f}", text_color="#00aa00", anchor="w", font=("Arial", 10)).pack(fill="x", padx=5)
            
            link = ctk.CTkEntry(card, width=400)
            link.insert(0, link_url)
            link.configure(state="readonly")
            link.pack(fill="x", padx=5, pady=5)
            self._create_context_menu(link)

    def export_results(self) -> None:
        """Экспорт результатов поиска в CSV файл."""
        if not self.current_search_results:
            messagebox.showwarning("Внимание", "Нет результатов для экспорта!")
            return
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"search_results_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['Название', 'Цена', 'Ссылка', 'Локация'])
                for item in self.current_search_results:
                    writer.writerow([
                        item.get('Название', ''),
                        item.get('Цена', ''),
                        item.get('Ссылка', ''),
                        item.get('Локация', '')
                    ])
            messagebox.showinfo("Успех", f"Результаты экспортированы в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")

    def export_to_excel(self) -> None:
        """Экспорт данных из таблицы в Excel (CSV с разделителями)."""
        filename = self.view_file_var.get()
        if not os.path.exists(filename):
            messagebox.showerror("Ошибка", "Выберите файл для экспорта!")
            return
        
        try:
            # Читаем исходный CSV
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=';')
                rows = list(reader)
            
            # Сохраняем как Excel-compatible CSV
            export_filename = f"export_{os.path.basename(filename)}"
            with open(export_filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerows(rows)
            
            messagebox.showinfo("Успех", f"Данные экспортированы в {export_filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")

    def export_to_json(self) -> None:
        """Экспорт данных из таблицы в JSON."""
        filename = self.view_file_var.get()
        if not os.path.exists(filename):
            messagebox.showerror("Ошибка", "Выберите файл для экспорта!")
            return
        
        try:
            # Читаем исходный CSV
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                data = list(reader)
            
            # Сохраняем как JSON
            export_filename = f"export_{os.path.splitext(os.path.basename(filename))[0]}.json"
            with open(export_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("Успех", f"Данные экспортированы в {export_filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")

if __name__ == "__main__":
    app = AvitoApp()
    app.mainloop()
