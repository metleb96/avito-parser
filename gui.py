import tkinter as tk
import customtkinter as ctk
import threading
import sys
import io
import os
import datetime
import glob
from tkinter import messagebox

# Импортируем наши модули
# (убедитесь, что main.py, processor.py, vectorizer.py находятся в той же папке)
from main import AvitoParser
from processor import DataProcessor
from vectorizer import AvitoVectorizer
from sentence_transformers import SentenceTransformer, util
import json
import csv

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
        """Вкладка Парсинга"""
        frame = self.tab_parser
        
        # Инпут URL
        ctk.CTkLabel(frame, text="URL Категории (Avito):").pack(pady=(10, 5))
        self.url_entry = ctk.CTkEntry(frame, width=600, placeholder_text="https://www.avito.ru/...")
        self.url_entry.pack(pady=5)
        self._create_context_menu(self.url_entry)

        # Инпут Pages

        # Инпут Pages
        ctk.CTkLabel(frame, text="Количество страниц:").pack(pady=(10, 5))
        self.pages_slider = ctk.CTkSlider(frame, from_=1, to=10, number_of_steps=9, width=400)
        self.pages_slider.pack(pady=5)
        self.pages_label = ctk.CTkLabel(frame, text="1")
        self.pages_label.pack()
        self.pages_slider.configure(command=lambda val: self.pages_label.configure(text=str(int(val))))
        
        self.pages_slider.configure(command=lambda val: self.pages_label.configure(text=str(int(val))))
        
        # Режим хранения
        ctk.CTkLabel(frame, text="Режим записи данных:").pack(pady=(10, 5))
        self.storage_mode = ctk.CTkSegmentedButton(frame, values=["Перезаписать", "Дополнить", "Новый файл"])
        self.storage_mode.set("Перезаписать")
        self.storage_mode.pack(pady=5)

        self.start_btn = ctk.CTkButton(frame, text="Запустить парсинг", command=self.start_parsing, fg_color="green")
        self.start_btn.pack(pady=20)

        # Консоль
        ctk.CTkLabel(frame, text="Лог работы:").pack(pady=(10, 5), anchor="w")
        self.log_box = ctk.CTkTextbox(frame, height=300)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_box.configure(state="disabled")

    def _setup_process_tab(self):
        """Вкладка Обработки данных"""
        frame = self.tab_process
        
        ctk.CTkLabel(frame, text="Этап 1: Очистка данных", font=("Arial", 16, "bold")).pack(pady=20)
        ctk.CTkButton(frame, text="Запустить очистку (Processor)", command=self.run_processor).pack(pady=10)
        self.clean_status = ctk.CTkLabel(frame, text="Статус: Ожидание", text_color="gray")
        self.clean_status.pack()

        ctk.CTkLabel(frame, text="Этап 2: Векторизация (AI)", font=("Arial", 16, "bold")).pack(pady=20)
        ctk.CTkButton(frame, text="Создать эмбеддинги (Vectorizer)", command=self.run_vectorizer, fg_color="#5500aa").pack(pady=10)
        self.vector_status = ctk.CTkLabel(frame, text="Статус: Ожидание", text_color="gray")
        self.vector_status.pack()

        self.process_log = ctk.CTkTextbox(frame, height=200)
        self.process_log.pack(fill="both", expand=True, padx=20, pady=20)
        self.process_log.configure(state="disabled")

    def _setup_search_tab(self):
        """Вкладка Поиска"""
        frame = self.tab_search

        ctk.CTkLabel(frame, text="Умный поиск по базе", font=("Arial", 18)).pack(pady=10)
        
        self.query_entry = ctk.CTkEntry(frame, width=500, placeholder_text="Например: игровой пк для киберпанка")
        self.query_entry.pack(pady=10)
        self._create_context_menu(self.query_entry)
        
        ctk.CTkButton(frame, text="Найти", command=self.run_search).pack(pady=10)

        self.results_frame = ctk.CTkScrollableFrame(frame, width=800, height=500)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def _setup_view_tab(self):
        """Вкладка Просмотра данных"""
        frame = self.tab_view
        
        # Управление
        ctrl_frame = ctk.CTkFrame(frame)
        ctrl_frame.pack(fill="x", padx=10, pady=10)
        
        self.view_file_var = ctk.StringVar(value="")
        self.file_combo = ctk.CTkComboBox(ctrl_frame, values=[], variable=self.view_file_var, width=300)
        self.file_combo.pack(side="left", padx=10)
        
        ctk.CTkButton(ctrl_frame, text="🔄 Обновить список", width=120, command=self.refresh_file_list).pack(side="left", padx=5)
        ctk.CTkButton(ctrl_frame, text="Загрузить (Топ 50)", command=self.load_table_data).pack(side="left", padx=10)
        
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

    def start_parsing(self):
        url = self.url_entry.get()
        pages = int(self.pages_slider.get())
        mode = self.storage_mode.get()
        
        if not url:
            messagebox.showerror("Ошибка", "Введите URL!")
            return

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

        self.start_btn.configure(state="disabled", text="Работает...")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        threading.Thread(target=self._parsing_thread, args=(url, pages, filename, append), daemon=True).start()

    def _parsing_thread(self, url, pages, filename, append):
        self.redirect_logging(self.log_box)
        try:
            print(f"[GUI] Старт. Файл: {filename}, Режим: {'Append' if append else 'Overwrite'}")
            parser = AvitoParser(output_file=filename)
            parser.run(url, pages, append=append)
            print("\n[GUI] Парсинг завершен!")
        except Exception as e:
            print(f"\n[GUI] Ошибка: {e}")
        finally:
            self.reset_logging()
            self.start_btn.configure(state="normal", text="Запустить парсинг")

    def run_processor(self):
        self.redirect_logging(self.process_log)
        self.clean_status.configure(text="Статус: В работе...", text_color="yellow")
        
        def task():
            try:
                proc = DataProcessor()
                proc.process()
                self.clean_status.configure(text="Статус: Готово ✅", text_color="green")
            except Exception as e:
                print(e)
                self.clean_status.configure(text="Статус: Ошибка ❌", text_color="red")
            finally:
                self.reset_logging()

        threading.Thread(target=task, daemon=True).start()

    def run_vectorizer(self):
        self.redirect_logging(self.process_log)
        self.vector_status.configure(text="Статус: В работе...", text_color="yellow")
        
        def task():
            try:
                vec = AvitoVectorizer()
                vec.process_data()
                self.vector_status.configure(text="Статус: Готово ✅", text_color="green")
                # Reset loaded data so search tab reloads it
                self.vector_data = None 
            except Exception as e:
                print(e)
                self.vector_status.configure(text="Статус: Ошибка ❌", text_color="red")
            finally:
                self.reset_logging()

        threading.Thread(target=task, daemon=True).start()

    def run_search(self):
        query = self.query_entry.get()
        if not query: return
        
        # Очистка результатов
        for widget in self.results_frame.winfo_children():
            widget.destroy()
            
        threading.Thread(target=self._search_thread, args=(query,), daemon=True).start()

    def _search_thread(self, query):
        try:
            # 1. Загрузка модели и данных (если еще нет)
            # 1. Загрузка модели и данных (если еще нет)
            if self.model is None:
                # Используем более мощную многоязычную модель
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            
            if self.vector_data is None:
                if not os.path.exists('vectorized_data.json'):
                    self.results_frame.configure(label_text="Ошибка: Файл vectorized_data.json не найден")
                    return
                with open('vectorized_data.json', 'r', encoding='utf-8') as f:
                    self.vector_data = json.load(f)

            # 2. Поиск
            query_embedding = self.model.encode(query, convert_to_tensor=True)
            
            # Собираем эмбеддинги из данных
            # Важно: util.semantic_search ожидает Tensor или numpy array,
            # но из JSON они приходят как списки.
            # Convert to tensor using the model's device
            import torch
            corpus_embeddings = torch.tensor([item['embedding'] for item in self.vector_data])
            
            # Считаем косинусное сходство
            hits = util.semantic_search(query_embedding, corpus_embeddings, top_k=10)
            
            # 3. GUI Update (нужно через after или schedule, но для простоты здесь напрямую, так как ctk толерантен, но лучше аккуратно)
            # CTK не полностью thread-safe. Лучше так:
            self.after(0, lambda: self._display_results(hits[0]))

        except Exception as e:
            print(f"Search Error: {e}")
            self.results_frame.configure(label_text=f"Ошибка поиска: {e}")

    def _display_results(self, hits):
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

if __name__ == "__main__":
    app = AvitoApp()
    app.mainloop()
