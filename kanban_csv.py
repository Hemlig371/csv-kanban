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
CLOSE_HOVER = "#e81123"    


class EditCardDialog(tk.Toplevel):

    def __init__(self, parent, row_data, headers, is_new=False):
        super().__init__(parent)
        self.title("Новая запись" if is_new else "Редактирование записи")
        self.geometry("450x550")
        self.configure(bg=BG_MAIN)
        self.transient(parent)
        self.grab_set()

        self.headers = headers
        self.result = None

        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg=BG_MAIN)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=BG_MAIN)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        # Привязка скролла мыши в диалоговом окне
        self.bind_mouse_wheel(canvas)

        self.entries = {}
        for header in self.headers:
            frame = tk.Frame(self.scrollable_frame, bg=BG_MAIN)
            frame.pack(fill="x", pady=5, padx=5)

            lbl = tk.Label(frame, text=header, font=("Arial", 10, "bold"), fg=FG_TEXT, bg=BG_MAIN)
            lbl.pack(anchor="w")

            entry = tk.Entry(
                frame, 
                width=45, 
                bg=BG_CARD, 
                fg=FG_TEXT, 
                insertbackground=FG_TEXT, 
                relief="solid", 
                bd=1,
                highlightthickness=1,
                highlightbackground=BORDER_COLOR,
                highlightcolor=ACCENT_COLOR
            )
            entry.insert(0, str(row_data.get(header, "")))
            entry.pack(fill="x", pady=4, ipady=4)
            self.entries[header] = entry

        btn_frame = tk.Frame(self, bg=BG_PANEL)
        btn_frame.pack(fill="x", side="bottom", ipady=10)

        cancel_btn = tk.Button(
            btn_frame, text="Отмена", command=self.destroy,
            bg=BG_CARD, fg=FG_TEXT, relief="flat", bd=0, padx=15, pady=5, activebackground=BORDER_COLOR, activeforeground=FG_TEXT
        )
        cancel_btn.pack(side="right", padx=10)

        save_btn = tk.Button(
            btn_frame, text="Сохранить", command=self.save,
            bg=ACCENT_COLOR, fg="white", relief="flat", bd=0, padx=15, pady=5, activebackground="#0062a3", activeforeground="white"
        )
        save_btn.pack(side="right", padx=5)

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def bind_mouse_wheel(self, widget):
        widget.bind_all("<MouseWheel>", lambda e: widget.yview_scroll(int(-1 * (e.delta / 120)), "units"))


class KanbanCSVApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("CSV Kanban Editor")
        self.geometry("1200x750")
        self.configure(bg=BG_MAIN)

        # Включаем Borderless режим (убираем стандартную рамку ОС)
        self.overrideredirect(True)

        self.file_path = None
        self.headers = []
        self.data = []
        self.csv_dialect = None
        self.kanban_column = None
        self._is_maximized = False

        # Переменные для перетаскивания окна мышкой
        self._drag_data = {"x": 0, "y": 0}

        self.setup_styles()
        self.init_custom_title_bar()
        self.init_main_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TFrame", background=BG_MAIN)
        style.configure("TopBar.TFrame", background=BG_PANEL)
        style.configure("TLabel", background=BG_MAIN, foreground=FG_TEXT)
        style.configure("Status.TLabel", background=BG_PANEL, foreground=FG_TEXT)
        style.configure("TCombobox", fieldbackground=BG_CARD, background=BG_PANEL, foreground=FG_TEXT, arrowcolor=FG_TEXT)
        style.configure("Vertical.TScrollbar", gripcount=0, background=BG_PANEL, darkcolor=BG_MAIN, lightcolor=BG_MAIN, troughcolor=BG_MAIN, bordercolor=BG_MAIN)
        style.configure("Horizontal.TScrollbar", gripcount=0, background=BG_PANEL, darkcolor=BG_MAIN, lightcolor=BG_MAIN, troughcolor=BG_MAIN, bordercolor=BG_MAIN)

    def init_custom_title_bar(self):
        """Создает кастомный заголовок окна со встроенным управлением"""
        self.title_bar = tk.Frame(self, bg=BG_PANEL, height=32)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.pack_propagate(False)

        # Иконка/Заголовок приложения
        title_label = tk.Label(self.title_bar, text=" 📋 CSV Kanban Editor", fg=FG_TEXT, bg=BG_PANEL, font=("Arial", 9, "bold"))
        title_label.pack(side="left", padx=10)

        # Кнопки управления окном (справа налево)
        close_btn = tk.Button(self.title_bar, text="✕", bg=BG_PANEL, fg=FG_TEXT, bd=0, font=("Arial", 10), width=5, height=2,
                              activebackground=CLOSE_HOVER, activeforeground="white", command=self.quit)
        close_btn.pack(side="right")
        close_btn.bind("<Enter>", lambda e: close_btn.config(bg=CLOSE_HOVER))
        close_btn.bind("<Leave>", lambda e: close_btn.config(bg=BG_PANEL))

        self.max_btn = tk.Button(self.title_bar, text="🗖", bg=BG_PANEL, fg=FG_TEXT, bd=0, font=("Arial", 10), width=5, height=2,
                                 activebackground=BORDER_COLOR, activeforeground=FG_TEXT, command=self.toggle_maximize)
        self.max_btn.pack(side="right")

        min_btn = tk.Button(self.title_bar, text="🗕", bg=BG_PANEL, fg=FG_TEXT, bd=0, font=("Arial", 10), width=5, height=2,
                             activebackground=BORDER_COLOR, activeforeground=FG_TEXT, command=self.minimize_window)
        min_btn.pack(side="right")

        # Бинды для перетаскивания окна за заголовок
        self.title_bar.bind("<Button-1>", self.start_drag)
        self.title_bar.bind("<B1-Motion>", self.拖动_drag)
        title_label.bind("<Button-1>", self.start_drag)
        title_label.bind("<B1-Motion>", self.拖动_drag)

    def start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def 拖动_drag(self, event):
        if self._is_maximized:
            return
        x = self.winfo_x() - self._drag_data["x"] + event.x
        y = self.winfo_y() - self._drag_data["y"] + event.y
        self.geometry(f"+{x}+{y}")

    def toggle_maximize(self):
        if self._is_maximized:
            self.geometry("1200x750")
            self.max_btn.config(text="🗖")
            self._is_maximized = False
        else:
            self.state('zoomed')
            self.max_btn.config(text="🗗")
            self._is_maximized = True

    def minimize_window(self):
        self.update_idletasks()
        self.overrideredirect(False)
        self.iconify()
        self.bind("<FocusIn>", self.restore_borderless)

    def restore_borderless(self, event):
        self.unbind("<FocusIn>")
        self.overrideredirect(True)

    def init_main_ui(self):
        # Постоянно видимая верхняя панель управления с системными кнопками Файла
        self.top_bar = ttk.Frame(self, padding=5, style="TopBar.TFrame")
        self.top_bar.pack(fill="x", side="top")

        # Кнопки операций с файлами (теперь всегда на виду!)
        self.btn_open = tk.Button(
            self.top_bar, text="Открыть CSV (Ctrl+O)", command=self.open_file,
            bg=BG_CARD, fg=FG_TEXT, relief="solid", bd=1, highlightthickness=0, padx=10, pady=4, activebackground=BORDER_COLOR, activeforeground=FG_TEXT
        )
        self.btn_open.pack(side="left", padx=5)

        self.btn_save = tk.Button(
            self.top_bar, text="Сохранить (Ctrl+S)", command=self.save_file,
            bg=BG_CARD, fg=FG_TEXT, relief="solid", bd=1, highlightthickness=0, padx=10, pady=4, activebackground=BORDER_COLOR, activeforeground=FG_TEXT
        )
        self.btn_save.pack(side="left", padx=5)

        # Кнопки динамических действий (пакуются справа по требованию)
        self.btn_change_col = tk.Button(
            self.top_bar, text="Сменить колонку доски", command=self.choose_kanban_column,
            bg=BG_CARD, fg=FG_TEXT, relief="solid", bd=1, highlightthickness=0, padx=10, pady=4, activebackground=BORDER_COLOR, activeforeground=FG_TEXT
        )
        
        self.btn_add_card = tk.Button(
            self.top_bar, text="+ Добавить запись", command=self.add_new_card,
            bg=ACCENT_COLOR, fg="white", relief="flat", bd=0, padx=12, pady=4, font=("Arial", 9, "bold"), activebackground="#0062a3", activeforeground="white"
        )

        # Строка статуса/информации о файле
        self.lbl_status = ttk.Label(
            self.top_bar, text="Файл не загружен.", font=("Arial", 9, "italic"), style="Status.TLabel"
        )
        self.lbl_status.pack(side="left", padx=15)

        # Контейнер для адаптивной Канбан-доски (Grid-основа для масштабирования)
        self.main_container = tk.Frame(self, bg=BG_MAIN)
        self.main_container.pack(fill="both", expand=True, padx=8, pady=8)

        # Бинды горячих клавиш
        self.bind_all("<Control-o>", lambda e: self.open_file())
        self.bind_all("<Control-s>", lambda e: self.save_file())

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if not lines:
                raise ValueError("Файл пустой.")

            first_line = lines[0]
            possible_delimiters = [';', ',', '\t']
            detected_delimiter = ','
            max_count = -1
            for d in possible_delimiters:
                count = first_line.count(d)
                if count > max_count:
                    max_count = count
                    detected_delimiter = d

            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=detected_delimiter)
                self.headers = reader.fieldnames
                self.data = list(reader)

            if not self.headers:
                raise ValueError("Не удалось определить заголовки.")

            self.file_path = file_path
            
            class CustomDialect(csv.excel):
                delimiter = detected_delimiter
            self.csv_dialect = CustomDialect
            
            self.lbl_status.config(text=f"Выбран: {os.path.basename(file_path)} | Строк: {len(self.data)}")
            
            self.btn_change_col.pack(side="right", padx=5)
            self.btn_add_card.pack(side="right", padx=5)
            
            self.choose_kanban_column()

        except Exception as e:
            messagebox.showerror("Ошибка парсинга CSV", f"Не удалось прочитать файл:\n{str(e)}")

    def choose_kanban_column(self):
        win = tk.Toplevel(self)
        win.title("Выбор колонки")
        win.geometry("350x160")
        win.configure(bg=BG_MAIN)
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="Выберите колонку для распределения:", bg=BG_MAIN, fg=FG_TEXT).pack(pady=15)
        combo = ttk.Combobox(win, values=self.headers, state="readonly")
        combo.pack(padx=20, pady=5, fill="x")
        
        if self.kanban_column in self.headers:
            combo.set(self.kanban_column)
        elif self.headers:
            combo.current(0)

        def confirm():
            self.kanban_column = combo.get()
            win.destroy()
            self.build_board()

        tk.Button(win, text="Построить доску", command=confirm, bg=ACCENT_COLOR, fg="white", relief="flat", bd=0, padx=15, pady=6).pack(pady=15)
        
        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (win.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (win.winfo_height() // 2)
        win.geometry(f"+{x}+{y}")

    def build_board(self):
        # Очищаем контейнер
        for child in self.main_container.winfo_children():
            child.destroy()

        if not self.kanban_column:
            return

        unique_values = set()
        for row in self.data:
            val = str(row.get(self.kanban_column, "")).strip()
            unique_values.add(val)
        
        sorted_values = sorted(list(unique_values))
        if "" in sorted_values:
            sorted_values.remove("")
            sorted_values.append("")

        num_columns = len(sorted_values)

        # Конфигурируем Grid-адаптивность: раздаем колонкам равный вес
        for col_idx in range(num_columns):
            self.main_container.grid_columnconfigure(col_idx, weight=1, uniform="equal_cols")
        self.main_container.grid_rowconfigure(0, weight=1)

        for col_idx, col_value in enumerate(sorted_values):
            col_title = col_value if col_value else "[Пусто]"

            col_frame = tk.Frame(self.main_container, bg=BG_PANEL, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
            col_frame.grid(row=0, column=col_idx, padx=4, pady=4, sticky="nsew")

            col_header = tk.Label(col_frame, text=col_title.upper(), bg=BG_PANEL, fg=FG_TEXT, font=("Arial", 10, "bold"), pady=6)
            col_header.pack(fill="x")

            # Внедряем скроллинг внутрь КАЖДОЙ колонки для длинных списков карточек
            canvas = tk.Canvas(col_frame, bg=BG_PANEL, borderwidth=0, highlightthickness=0)
            canvas.pack(fill="both", expand=True)

            cards_frame = tk.Frame(canvas, bg=BG_PANEL)
            canvas.create_window((0, 0), window=cards_frame, anchor="nw")

            # Автоматическая корректировка ширины прокручиваемой зоны под размер колонки
            def _configure_canvas(e, c=canvas, f=cards_frame):
                c.configure(scrollregion=c.bbox("all"))
                c.itemconfigure(1, width=e.width)

            canvas.bind("<Configure>", _configure_canvas)
            cards_frame.bind("<Configure>", lambda e, c=canvas: c.configure(scrollregion=c.bbox("all")))

            # Поддержка колесика мыши при наведении на колонку
            def _on_mousewheel(event, c=canvas):
                c.yview_scroll(int(-1 * (event.delta / 120)), "units")
            canvas.bind("<Enter>", lambda e, c=canvas: self.bind_all("<MouseWheel>", _on_mousewheel))
            canvas.bind("<Leave>", lambda e: self.unbind_all("<MouseWheel>"))

            has_cards = False
            for row_dict in self.data:
                val = str(row_dict.get(self.kanban_column, "")).strip()
                if val == col_value:
                    self.create_card(cards_frame, row_dict)
                    has_cards = True
            
            if not has_cards:
                placeholder = tk.Label(cards_frame, text="(Нет записей)", fg=FG_MUTED, bg=BG_PANEL, font=("Arial", 9, "italic"), pady=15)
                placeholder.pack(fill="x")

        self.update_idletasks()

    def create_card(self, parent, row_dict):
        card = tk.Frame(parent, bg=BG_CARD, bd=1, relief="solid", cursor="hand2", highlightbackground=BORDER_COLOR)
        card.pack(fill="x", padx=5, pady=5, anchor="n")

        preview_text = ""
        for h in self.headers[:4]:
            val = str(row_dict.get(h, ""))
            val_trunc = val[:25] + "..." if len(val) > 25 else val
            preview_text += f"• {h}: {val_trunc}\n"

        lbl = tk.Label(
            card, text=preview_text.strip(), bg=BG_CARD, fg=FG_TEXT, justify="left",
            anchor="w", font=("Arial", 9), padx=8, pady=8, wraplength=220
        )
        lbl.pack(fill="both", expand=True)

        # Пересчет wraplength при изменении размеров карточки (чтобы текст не обрезался)
        card.bind("<Configure>", lambda e, l=lbl: l.config(wraplength=max(100, e.width - 15)))

        def on_double_click(event, r=row_dict):
            self.edit_row(r)

        card.bind("<Double-1>", on_double_click)
        lbl.bind("<Double-1>", on_double_click)

    def edit_row(self, row_dict):
        dialog = EditCardDialog(self, row_dict, self.headers, is_new=False)
        self.wait_window(dialog)
        if dialog.result:
            row_dict.update(dialog.result)
            self.build_board()

    def add_new_card(self):
        if not self.file_path:
            return
        new_row_template = {h: "" for h in self.headers}
        if self.kanban_column:
            unique_vals = list(set(str(r.get(self.kanban_column, "")).strip() for r in self.data))
            if unique_vals:
                new_row_template[self.kanban_column] = unique_vals[0]

        dialog = EditCardDialog(self, new_row_template, self.headers, is_new=True)
        self.wait_window(dialog)
        if dialog.result:
            self.data.append(dialog.result)
            self.lbl_status.config(text=f"Выбран: {os.path.basename(self.file_path)} | Строк: {len(self.data)}")
            self.build_board()

    def save_file(self):
        if not self.file_path:
            messagebox.showwarning("Внимание", "Нет открытого файла для сохранения.")
            return
        try:
            with open(self.file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.headers, dialect=self.csv_dialect)
                writer.writeheader()
                writer.writerows(self.data)
            messagebox.showinfo("Успех", "Данные успешно сохранены!")
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить файл:\n{str(e)}")


if __name__ == "__main__":
    app = KanbanCSVApp()
    app.mainloop()
