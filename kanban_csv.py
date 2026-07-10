import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --- Константы цветовой схемы (Modern Dark) ---
BG_MAIN = "#1e1e1e"        
BG_PANEL = "#252526"       
BG_CARD = "#2d2d30"        
FG_TEXT = "#e1e1e1"        
FG_MUTED = "#858585"       
ACCENT_COLOR = "#007acc"   
BORDER_COLOR = "#3f3f46"   

PAGE_SIZE = 25  # Размер порции данных для ленивой загрузки в колонках


class EditCardDialog(tk.Toplevel):

    def __init__(self, parent, row_data, headers, text_column=None, is_new=False):
        super().__init__(parent)
        self.title("Новая запись" if is_new else "Редактирование записи")
        self.configure(bg=BG_MAIN)
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()

        self.headers = headers
        self.text_column = text_column
        self.result = None

        # Нижняя панель действий (всегда видна)
        btn_frame = tk.Frame(self, bg=BG_PANEL)
        btn_frame.pack(fill="x", side="bottom", ipady=10)

        cancel_btn = tk.Button(
            btn_frame, text="Отмена", command=self.destroy, font=("Arial", 12),
            bg=BG_CARD, fg=FG_TEXT, relief="flat", bd=0, padx=20, pady=6, activebackground=BORDER_COLOR, activeforeground=FG_TEXT
        )
        cancel_btn.pack(side="right", padx=15)

        save_btn = tk.Button(
            btn_frame, text="Сохранить", command=self.save, font=("Arial", 12, "bold"),
            bg=ACCENT_COLOR, fg="white", relief="flat", bd=0, padx=20, pady=6, activebackground="#0062a3", activeforeground="white"
        )
        save_btn.pack(side="right", padx=5)

        # Скролл-контейнер контента
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg=BG_MAIN)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=BG_MAIN)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas_frame_id = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(canvas_frame_id, width=event.width))
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        def _on_dialog_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind("<MouseWheel>", _on_dialog_wheel)
        self.scrollable_frame.bind("<MouseWheel>", _on_dialog_wheel)

        self.widgets = {}
        for header in self.headers:
            frame = tk.Frame(self.scrollable_frame, bg=BG_MAIN)
            frame.pack(fill="x", pady=6, padx=5)

            lbl = tk.Label(frame, text=header, font=("Arial", 11, "bold"), fg=FG_TEXT, bg=BG_MAIN)
            lbl.pack(anchor="w")

            if text_column and header == text_column:
                text_area = tk.Text(
                    frame, font=("Arial", 12), bg=BG_CARD, fg=FG_TEXT,
                    insertbackground=FG_TEXT, relief="solid", bd=1, height=5,
                    wrap="word", highlightthickness=1, highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_COLOR
                )
                text_area.insert("1.0", str(row_data.get(header, "")))
                text_area.pack(fill="x", pady=4)
                self.widgets[header] = text_area
                text_area.bind("<MouseWheel>", _on_dialog_wheel)
            else:
                entry = tk.Entry(
                    frame, font=("Arial", 12), bg=BG_CARD, fg=FG_TEXT,
                    insertbackground=FG_TEXT, relief="solid", bd=1,
                    highlightthickness=1, highlightbackground=BORDER_COLOR, highlightcolor=ACCENT_COLOR
                )
                entry.insert(0, str(row_data.get(header, "")))
                entry.pack(fill="x", pady=4, ipady=4)
                self.widgets[header] = entry
                entry.bind("<MouseWheel>", _on_dialog_wheel)

        self.initial_geometry(parent)

    def initial_geometry(self, parent):
        self.update_idletasks()
        width, height = 650, 700
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def save(self):
        self.result = {}
        for h in self.headers:
            w = self.widgets[h]
            self.result[h] = w.get("1.0", "end-1c").strip() if isinstance(w, tk.Text) else w.get().strip()
        self.grab_release()
        self.destroy()


class KanbanCSVApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("CSV Kanban Editor")
        self.configure(bg=BG_MAIN)

        self.file_path = None
        self.headers = []
        self.data = []
        self.csv_dialect = None
        self.kanban_column = None
        self.text_column = None
        
        # Индексы пагинации для ленивой загрузки колонок
        self.column_pages = {}
        self.column_data_map = {}

        self.setup_styles()
        self.init_main_ui()

        # Стартовые размеры (нативное системное окно)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width, height = 1500, 850
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure(".", background=BG_MAIN, foreground=FG_TEXT)
        style.configure("TopBar.TFrame", background=BG_PANEL)
        style.configure("TLabel", background=BG_MAIN, foreground=FG_TEXT, font=("Arial", 12))
        style.configure("Status.TLabel", background=BG_PANEL, foreground=FG_TEXT, font=("Arial", 11, "italic"))
        style.configure("TCombobox", font=("Arial", 12), fieldbackground=BG_CARD, background=BG_PANEL, foreground=FG_TEXT, arrowcolor=FG_TEXT)
        style.configure("Vertical.TScrollbar", gripcount=0, background=BG_PANEL, troughcolor=BG_MAIN, bordercolor=BG_MAIN)

    def init_main_ui(self):
        self.top_bar = ttk.Frame(self, padding=6, style="TopBar.TFrame")
        self.top_bar.pack(fill="x", side="top")

        self.btn_open = tk.Button(
            self.top_bar, text="Открыть CSV (Ctrl+O)", command=self.open_file, font=("Arial", 11),
            bg=BG_CARD, fg=FG_TEXT, relief="solid", bd=1, padx=12, pady=4, activebackground=BORDER_COLOR, activeforeground=FG_TEXT
        )
        self.btn_open.pack(side="left", padx=5)

        self.btn_save = tk.Button(
            self.top_bar, text="Сохранить (Ctrl+S)", command=self.save_file, font=("Arial", 11),
            bg=BG_CARD, fg=FG_TEXT, relief="solid", bd=1, padx=12, pady=4, activebackground=BORDER_COLOR, activeforeground=FG_TEXT
        )
        self.btn_save.pack(side="left", padx=5)

        self.btn_change_col = tk.Button(
            self.top_bar, text="Настройка колонок", command=self.setup_kanban_columns_dialog, font=("Arial", 11),
            bg=BG_CARD, fg=FG_TEXT, relief="solid", bd=1, padx=12, pady=4, activebackground=BORDER_COLOR, activeforeground=FG_TEXT
        )
        
        self.btn_add_card = tk.Button(
            self.top_bar, text="+ Добавить запись", command=self.add_new_card, font=("Arial", 11, "bold"),
            bg=ACCENT_COLOR, fg="white", relief="flat", bd=0, padx=15, pady=4, activebackground="#0062a3", activeforeground="white"
        )

        self.lbl_status = ttk.Label(self.top_bar, text="Файл не загружен.", style="Status.TLabel")
        self.lbl_status.pack(side="left", padx=15)

        self.main_container = tk.Frame(self, bg=BG_MAIN)
        self.main_container.pack(fill="both", expand=True, padx=8, pady=8)

        self.bind_all("<Control-o>", lambda e: self.open_file())
        self.bind_all("<Control-s>", lambda e: self.save_file())

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [f.readline() for _ in range(5)]
            if not lines:
                raise ValueError("Файл пустой.")

            detected_delimiter = ';' if ';' in lines[0] else (',' if ',' in lines[0] else '\t')

            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=detected_delimiter)
                self.headers = reader.fieldnames
                self.data = list(reader)

            if not self.headers:
                raise ValueError("Не удалось определить структуру CSV.")

            self.file_path = file_path
            class CustomDialect(csv.excel): delimiter = detected_delimiter
            self.csv_dialect = CustomDialect
            
            self.lbl_status.config(text=f"Файл: {os.path.basename(file_path)} | Строк: {len(self.data)}")
            
            self.btn_change_col.pack(side="right", padx=5)
            self.btn_add_card.pack(side="right", padx=5)
            
            self.setup_kanban_columns_dialog()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{str(e)}")

    def setup_kanban_columns_dialog(self):
        win = tk.Toplevel(self)
        win.title("Конфигурация доски")
        win.configure(bg=BG_MAIN)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        
        tk.Label(win, text="Группировать по колонке:", bg=BG_MAIN, font=("Arial", 11, "bold")).pack(pady=(15, 2), padx=20, anchor="w")
        combo_kanban = ttk.Combobox(win, values=self.headers, state="readonly", font=("Arial", 11))
        combo_kanban.pack(padx=20, pady=5, fill="x")
        combo_kanban.set(self.kanban_column if self.kanban_column in self.headers else self.headers[0])

        tk.Label(win, text="Поле многострочного текста (Textarea):", bg=BG_MAIN, font=("Arial", 11, "bold")).pack(pady=(15, 2), padx=20, anchor="w")
        combo_text = ttk.Combobox(win, values=["[Нет]"] + self.headers, state="readonly", font=("Arial", 11))
        combo_text.pack(padx=20, pady=5, fill="x")
        combo_text.set(self.text_column if self.text_column in self.headers else "[Нет]")

        def confirm():
            self.kanban_column = combo_kanban.get()
            selected_txt = combo_text.get()
            self.text_column = None if selected_txt == "[Нет]" else selected_txt
            win.grab_release()
            win.destroy()
            self.build_board()

        tk.Button(win, text="Построить доску", command=confirm, bg=ACCENT_COLOR, fg="white", relief="flat", font=("Arial", 11, "bold"), pady=6).pack(pady=20)
        
        win.update_idletasks()
        w, h = 400, 250
        x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

    def build_board(self):
        for child in self.main_container.winfo_children():
            child.destroy()

        if not self.kanban_column:
            return

        # Индексация данных в хэш-таблицу (O(N) вместо O(N^2)) — критично для 10k строк
        self.column_data_map = {}
        for row in self.data:
            val = str(row.get(self.kanban_column, "")).strip()
            if val not in self.column_data_map:
                self.column_data_map[val] = []
            self.column_data_map[val].append(row)

        sorted_values = sorted(list(self.column_data_map.keys()))
        num_columns = len(sorted_values)

        for col_idx in range(num_columns):
            self.main_container.grid_columnconfigure(col_idx, weight=1, uniform="equal_cols")
        self.main_container.grid_rowconfigure(0, weight=1)

        for col_idx, col_value in enumerate(sorted_values):
            col_title = col_value if col_value else "[Пусто]"
            rows_in_col = self.column_data_map[col_value]

            col_frame = tk.Frame(self.main_container, bg=BG_PANEL, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
            col_frame.grid(row=0, column=col_idx, padx=4, pady=4, sticky="nsew")

            col_header = tk.Label(col_frame, text=f"{col_title.upper()} ({len(rows_in_col)})", bg=BG_PANEL, fg=FG_TEXT, font=("Arial", 11, "bold"), pady=8)
            col_header.pack(fill="x")

            canvas = tk.Canvas(col_frame, bg=BG_PANEL, borderwidth=0, highlightthickness=0)
            canvas.pack(fill="both", expand=True)

            cards_frame = tk.Frame(canvas, bg=BG_PANEL)
            canvas.create_window((0, 0), window=cards_frame, anchor="nw")

            # Инициализируем пагинацию для данной колонки
            self.column_pages[col_value] = PAGE_SIZE

            def _config_canvas(e, c=canvas, f=cards_frame):
                c.configure(scrollregion=c.bbox("all"))
                c.itemconfigure(1, width=e.width)

            canvas.bind("<Configure>", _config_canvas)

            # Ленивый рендеринг при скроллинге вниз
            def _on_scroll_wheel(event, cv=canvas, val=col_value, frame=cards_frame):
                cv.yview_scroll(int(-1 * (event.delta / 120)), "units")
                # Если докрутили до низа — подгружаем следующую пачку данных
                if cv.yview()[1] >= 0.9 if cv.yview()[1] else 1.0:
                    self.load_more_cards(val, frame, cv)

            canvas.bind("<MouseWheel>", _on_scroll_wheel)
            cards_frame.bind("<MouseWheel>", _on_scroll_wheel)

            # Первая порция отрисовки
            self.render_cards_chunk(col_value, cards_frame, 0, PAGE_SIZE, _on_scroll_wheel)

    def render_cards_chunk(self, col_value, target_frame, start_idx, end_idx, wheel_handler):
        rows = self.column_data_map[col_value]
        chunk = rows[start_idx:end_idx]

        if start_idx == 0 and not chunk:
            placeholder = tk.Label(target_frame, text="(Нет записей)", fg=FG_MUTED, bg=BG_PANEL, font=("Arial", 11, "italic"), pady=15)
            placeholder.pack(fill="x")
            return

        for row_dict in chunk:
            card = tk.Frame(target_frame, bg=BG_CARD, bd=1, relief="solid", cursor="hand2", highlightbackground=BORDER_COLOR)
            card.pack(fill="x", padx=6, pady=5, anchor="n")

            preview_text = ""
            for h in self.headers[:4]:
                val = str(row_dict.get(h, ""))
                val_trunc = val[:35] + "..." if len(val) > 35 else val
                preview_text += f"• {h}: {val_trunc}\n"

            lbl = tk.Label(
                card, text=preview_text.strip(), bg=BG_CARD, fg=FG_TEXT, justify="left",
                anchor="w", font=("Arial", 11), padx=8, pady=8, wraplength=280
            )
            lbl.pack(fill="both", expand=True)

            card.bind("<Configure>", lambda e, l=lbl: l.config(wraplength=max(120, e.width - 15)))
            card.bind("<MouseWheel>", wheel_handler)
            lbl.bind("<MouseWheel>", wheel_handler)

            # Замыкание ссылки на словарь строки
            def make_click_handler(r=row_dict):
                return lambda e: self.edit_row(r)

            card.bind("<Double-1>", make_click_handler())
            lbl.bind("<Double-1>", make_click_handler())

    def load_more_cards(self, col_value, target_frame, canvas):
        current_limit = self.column_pages[col_value]
        total_rows = len(self.column_data_map[col_value])
        
        if current_limit >= total_rows:
            return  # Все данные уже на экране

        next_limit = current_limit + PAGE_SIZE
        self.column_pages[col_value] = next_limit
        
        # Рендерим только новую маленькую порцию, не трогая старые виджеты
        self.render_cards_chunk(col_value, target_frame, current_limit, next_limit, lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        canvas.configure(scrollregion=canvas.bbox("all"))

    def edit_row(self, row_dict):
        dialog = EditCardDialog(self, row_dict, self.headers, text_column=self.text_column, is_new=False)
        self.wait_window(dialog)
        if dialog.result:
            row_dict.update(dialog.result)
            self.build_board()

    def add_new_card(self):
        if not self.file_path: return
        new_row = {h: "" for h in self.headers}
        if self.kanban_column and self.column_data_map:
            new_row[self.kanban_column] = list(self.column_data_map.keys())[0]

        dialog = EditCardDialog(self, new_row, self.headers, text_column=self.text_column, is_new=True)
        self.wait_window(dialog)
        if dialog.result:
            self.data.append(dialog.result)
            self.lbl_status.config(text=f"Файл: {os.path.basename(self.file_path)} | Строк: {len(self.data)}")
            self.build_board()

    def save_file(self):
        if not self.file_path: return
        try:
            with open(self.file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.headers, dialect=self.csv_dialect)
                writer.writeheader()
                writer.writerows(self.data)
            messagebox.showinfo("Успех", "Сохранено!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{str(e)}")


if __name__ == "__main__":
    app = KanbanCSVApp()
    app.mainloop()
