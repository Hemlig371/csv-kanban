import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --- Константы цветовой схемы (Dark Theme) ---
BG_MAIN = "#1e1e1e"        # Главный фон приложения
BG_PANEL = "#252526"       # Фон панелей и колонок
BG_CARD = "#2d2d30"        # Фон карточек
FG_TEXT = "#e1e1e1"        # Основной текст
FG_MUTED = "#858585"       # Тусклый текст (для подписей и пустых колонок)
ACCENT_COLOR = "#007acc"   # Акцентный синий цвет (для кнопок)
BORDER_COLOR = "#3f3f46"   # Цвет границ


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

        # Стилизация Canvas под темную тему
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg=BG_MAIN)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg=BG_MAIN)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, py=10)
        scrollbar.pack(side="right", fill="y")

        self.entries = {}
        for header in self.headers:
            frame = tk.Frame(self.scrollable_frame, bg=BG_MAIN)
            frame.pack(fill="x", pady=5, padx=5)

            lbl = tk.Label(frame, text=header, font=("Arial", 10, "bold"), fg=FG_TEXT, bg=BG_MAIN)
            lbl.pack(anchor="w")

            # Кастомное текстовое поле для соответствия темной теме
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

        btn_frame = tk.Frame(self, bg=BG_PANEL, padding=10)
        btn_frame.pack(fill="x", side="bottom")

        # Кнопки управления в диалоге
        cancel_btn = tk.Button(
            btn_frame, text="Отмена", command=self.destroy,
            bg=BG_CARD, fg=FG_TEXT, relief="flat", bd=0, padx=15, pady=5, activebackground=BORDER_COLOR, activeforeground=FG_TEXT
        )
        cancel_btn.pack(side="right", padx=5)

        save_btn = tk.Button(
            btn_frame, text="Сохранить", command=self.save,
            bg=ACCENT_COLOR, fg="white", relief="flat", bd=0, padx=15, pady=5, activebackground="#0062a3", activeforeground="white"
        )
        save_btn.pack(side="right", padx=5)

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def save(self):
        self.result = {h: self.entries[h].get() for h in self.headers}
        self.destroy()


class KanbanCSVApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("CSV Kanban Editor")
        self.geometry("1200x750")
        self.configure(bg=BG_MAIN)

        self.file_path = None
        self.headers = []
        self.data = []
        self.csv_dialect = None
        self.kanban_column = None

        self.setup_styles()
        self.init_menu()
        self.init_main_ui()

    def setup_styles(self):
        # Настройка глобальных стилей ttk под темную тему
        style = ttk.Style()
        style.theme_use("default")
        
        # Настройка статусбара и панелей
        style.configure("TFrame", background=BG_MAIN)
        style.configure("TopBar.TFrame", background=BG_PANEL)
        style.configure("TLabel", background=BG_MAIN, foreground=FG_TEXT)
        style.configure("Status.TLabel", background=BG_PANEL, foreground=FG_TEXT)
        
        # Стилизация выпадающего списка
        style.configure("TCombobox", fieldbackground=BG_CARD, background=BG_PANEL, foreground=FG_TEXT, arrowcolor=FG_TEXT)
        
        # Стилизация скроллбаров
        style.configure("Vertical.TScrollbar", gripcount=0, background=BG_PANEL, darkcolor=BG_MAIN, lightcolor=BG_MAIN, troughcolor=BG_MAIN, bordercolor=BG_MAIN)
        style.configure("Horizontal.TScrollbar", gripcount=0, background=BG_PANEL, darkcolor=BG_MAIN, lightcolor=BG_MAIN, troughcolor=BG_MAIN, bordercolor=BG_MAIN)

    def init_menu(self):
        menubar = tk.Menu(self, bg=BG_PANEL, fg=FG_TEXT, activebackground=ACCENT_COLOR, activeforeground="white", bd=0)
        file_menu = tk.Menu(menubar, tearoff=0, bg=BG_PANEL, fg=FG_TEXT, activebackground=ACCENT_COLOR, activeforeground="white", bd=0)
        file_menu.add_command(
            label="Открыть CSV...", command=self.open_file, accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Сохранить CSV", command=self.save_file, accelerator="Ctrl+S"
        )
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)
        self.config(menu=menubar)

        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_file())

    def init_main_ui(self):
        # Верхняя панель управления
        self.top_bar = ttk.Frame(self, padding=10, style="TopBar.TFrame")
        self.top_bar.pack(fill="x", side="top")

        self.lbl_status = ttk.Label(
            self.top_bar,
            text="Файл не выбран. Откройте CSV через меню (Ctrl+O)",
            font=("Arial", 10, "italic"),
            style="Status.TLabel"
        )
        self.lbl_status.pack(side="left", vertical_alignment="center")

        # Кнопки действий (будут упакованы программно после загрузки файла)
        self.btn_change_col = tk.Button(
            self.top_bar, text="Сменить колонку доски", command=self.choose_kanban_column,
            bg=BG_CARD, fg=FG_TEXT, relief="solid", bd=1, highlightthickness=0, padx=10, pady=5, activebackground=BORDER_COLOR, activeforeground=FG_TEXT
        )
        
        self.btn_add_card = tk.Button(
            self.top_bar, text="+ Добавить запись", command=self.add_new_card,
            bg=ACCENT_COLOR, fg="white", relief="flat", bd=0, padx=12, pady=5, font=("Arial", 9, "bold"), activebackground="#0062a3", activeforeground="white"
        )

        # Контейнер Канбан-доски
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True, padx=5, py=5)

        self.board_canvas = tk.Canvas(self.main_container, borderwidth=0, highlightthickness=0, bg=BG_MAIN)
        self.h_scrollbar = ttk.Scrollbar(
            self.main_container, orient="horizontal", command=self.board_canvas.xview
        )
        self.v_scrollbar = ttk.Scrollbar(
            self.main_container, orient="vertical", command=self.board_canvas.yview
        )

        self.board_frame = tk.Frame(self.board_canvas, bg=BG_MAIN)
        self.board_frame.bind(
            "<Configure>",
            lambda e: self.board_canvas.configure(scrollregion=self.board_canvas.bbox("all")),
        )

        self.board_canvas.create_window((0, 0), window=self.board_frame, anchor="nw")
        self.board_canvas.configure(
            xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set
        )

        self.h_scrollbar.pack(side="bottom", fill="x")
        self.v_scrollbar.pack(side="right", fill="y")
        self.board_canvas.pack(side="left", fill="both", expand=True)

    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            if not lines:
                raise ValueError("Файл абсолютно пустой.")

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
                raise ValueError("Не удалось определить заголовки полей.")

            self.file_path = file_path
            
            class CustomDialect(csv.excel):
                delimiter = detected_delimiter
            self.csv_dialect = CustomDialect
            
            self.lbl_status.config(
                text=f"Файл: {os.path.basename(file_path)} | Строк: {len(self.data)} | Разделитель: {repr(detected_delimiter)}"
            )
            
            # Показываем кнопки на верхней панели управления
            self.btn_change_col.pack(side="right", padx=5)
            self.btn_add_card.pack(side="right", padx=5)
            
            self.choose_kanban_column()

        except Exception as e:
            messagebox.showerror("Ошибка парсинга CSV", f"Не удалось прочитать структуру файла:\n{str(e)}")

    def choose_kanban_column(self):
        win = tk.Toplevel(self)
        win.title("Выбор колонки")
        win.geometry("350x160")
        win.configure(bg=BG_MAIN)
        win.transient(self)
        win.grab_set()

        tk.Label(
            win, text="Выберите колонку для Канбан-доски:", padding=10, justify="center", bg=BG_MAIN, fg=FG_TEXT
        ).pack()
        
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

        tk.Button(
            win, text="Построить доску", command=confirm,
            bg=ACCENT_COLOR, fg="white", relief="flat", bd=0, padx=15, pady=6, activebackground="#0062a3", activeforeground="white"
        ).pack(pady=15)
        
        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (win.winfo_width() // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (win.winfo_height() // 2)
        win.geometry(f"+{x}+{y}")

    def build_board(self):
        for child in self.board_frame.winfo_children():
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

        for col_idx, col_value in enumerate(sorted_values):
            col_title = col_value if col_value else "[Пусто]"

            # Кастомный фрейм под колонку (эмуляция LabelFrame с темным дизайном)
            col_frame = tk.Frame(self.board_frame, bg=BG_PANEL, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
            col_frame.grid(row=0, column=col_idx, padx=8, pady=8, sticky="nsew")

            col_header = tk.Label(
                col_frame, text=col_title.upper(), bg=BG_PANEL, fg=FG_TEXT, font=("Arial", 10, "bold"), pady=6
            )
            col_header.pack(fill="x")

            cards_frame = tk.Frame(col_frame, bg=BG_PANEL)
            cards_frame.pack(fill="both", expand=True, padx=4, pady=4)

            has_cards = False
            for row_dict in self.data:
                val = str(row_dict.get(self.kanban_column, "")).strip()
                if val == col_value:
                    self.create_card(cards_frame, row_dict)
                    has_cards = True
            
            col_frame.config(width=280)
            if not has_cards:
                placeholder = tk.Label(cards_frame, text="(Нет записей)", fg=FG_MUTED, bg=BG_PANEL, font=("Arial", 9, "italic"), pady=15)
                placeholder.pack()

        self.update_idletasks()
        self.board_canvas.configure(scrollregion=self.board_canvas.bbox("all"))

    def create_card(self, parent, row_dict):
        card = tk.Frame(
            parent, bg=BG_CARD, bd=1, relief="solid", cursor="hand2", highlightbackground=BORDER_COLOR
        )
        card.pack(fill="x", padx=5, pady=5, anchor="n")

        preview_text = ""
        for h in self.headers[:4]:
            val = str(row_dict.get(h, ""))
            val_trunc = val[:30] + "..." if len(val) > 30 else val
            preview_text += f"• {h}: {val_trunc}\n"

        lbl = tk.Label(
            card,
            text=preview_text.strip(),
            bg=BG_CARD,
            fg=FG_TEXT,
            justify="left",
            anchor="w",
            font=("Arial", 9),
            padx=8,
            py=8,
            wraplength=240
        )
        lbl.pack(fill="both", expand=True)

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
            
        # Создаем пустую болванку для новой строки структуры
        new_row_template = {h: "" for h in self.headers}
        
        # Если колонка доски выбрана, сразу подставляем её дефолтное значение из первой колонки, чтобы карточка не потерялась
        if self.kanban_column:
            # Пытаемся взять уникальные значения, чтобы положить карточку в первый существующий столбец
            unique_vals = list(set(str(r.get(self.kanban_column, "")).strip() for r in self.data))
            if unique_vals:
                new_row_template[self.kanban_column] = unique_vals[0]

        dialog = EditCardDialog(self, new_row_template, self.headers, is_new=True)
        self.wait_window(dialog)

        if dialog.result:
            # Добавляем новую запись в общий массив данных
            self.data.append(dialog.result)
            # Обновляем статусбар
            self.lbl_status.config(
                text=f"Файл: {os.path.basename(self.file_path)} | Строк: {len(self.data)} | Разделитель: {repr(self.csv_dialect.delimiter)}"
            )
            # Перестраиваем доску
            self.build_board()

    def save_file(self):
        if not self.file_path:
            messagebox.showwarning("Внимание", "Нет открытого файла для сохранения.")
            return

        try:
            with open(self.file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=self.headers, dialect=self.csv_dialect
                )
                writer.writeheader()
                writer.writerows(self.data)

            messagebox.showinfo("Успех", "Данные успешно сохранены в файл!")
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить файл:\n{str(e)}")


if __name__ == "__main__":
    app = KanbanCSVApp()
    app.mainloop()
