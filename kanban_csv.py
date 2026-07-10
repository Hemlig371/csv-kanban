import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class EditCardDialog(tk.Toplevel):

    def __init__(self, parent, row_data, headers):
        super().__init__(parent)
        self.title("Редактирование записи")
        self.geometry("400x500")
        self.transient(parent)
        self.grab_set()

        self.headers = headers
        self.result = None

        # Скроллбар для большого количества полей
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

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
            frame = ttk.Frame(self.scrollable_frame)
            frame.pack(fill="x", pady=5, expand=True)

            lbl = ttk.Label(frame, text=header, font=("Arial", 10, "bold"))
            lbl.pack(anchor="w")

            # Используем Text для многострочности или Entry для простоты
            entry = ttk.Entry(frame, width=40)
            entry.insert(0, row_data.get(header, ""))
            entry.pack(fill="x", pady=2)
            self.entries[header] = entry

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", side="bottom", pady=10, padx=10)

        ttk.Button(btn_frame, text="Отмена", command=self.destroy).pack(
            side="right", padx=5
        )
        ttk.Button(btn_frame, text="Сохранить", command=self.save).pack(
            side="right"
        )

    def save(self):
        self.result = {h: self.entries[h].get() for h in self.headers}
        self.destroy()


class KanbanCSVApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("CSV Kanban Editor")
        self.geometry("1100x700")

        self.file_path = None
        self.headers = []
        self.data = []  # Список словарей [ {header: value, ...}, ... ]
        self.csv_dialect = None
        self.kanban_column = None

        self.init_menu()
        self.init_main_ui()

    def init_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
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
        self.top_bar = ttk.Frame(self, padding=10)
        self.top_bar.pack(fill="x")

        self.lbl_status = ttk.Label(
            self.top_bar, text="Файл не выбран", font=("Arial", 10, "italic")
        )
        self.lbl_status.pack(side="left")

        # Контейнер для доски со скроллбарами
        self.board_canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.h_scrollbar = ttk.Scrollbar(
            self, orient="horizontal", command=self.board_canvas.xview
        )
        self.v_scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.board_canvas.yview
        )

        self.board_frame = ttk.Frame(self.board_canvas)
        self.board_frame.bind(
            "<Configure>",
            lambda e: self.board_canvas.configure(
                scrollregion=self.board_canvas.bbox("all")
            ),
        )

        self.board_canvas.create_window(
            (0, 0), window=self.board_frame, anchor="nw"
        )
        self.board_canvas.configure(
            xscrollcommand=self.h_scrollbar.set,
            yscrollcommand=self.v_scrollbar.set,
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
            # Читаем файл целиком, чтобы надежно определить разделитель
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            if not lines:
                raise ValueError("Файл абсолютно пустой.")

            first_line = lines[0]
            
            # Вручную ищем наиболее вероятный разделитель (запятая, точка с запятой или таб)
            possible_delimiters = [';', ',', '\t']
            delimiter = ',' # по умолчанию
            max_count = -1
            
            for d in possible_delimiters:
                count = first_line.count(d)
                if count > max_count:
                    max_count = count
                    delimiter = d

            # Читаем данные заново, используя гарантированный разделитель
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                self.headers = reader.fieldnames
                self.data = list(reader)

            # Проверяем, удалось ли вытащить заголовки
            if not self.headers or len(self.headers) <= 1 and delimiter not in first_line:
                # На случай, если в файле всего одна колонка без разделителей
                if self.headers:
                    pass
                else:
                    raise ValueError("Не удалось определить заголовки колонок.")

            self.file_path = file_path
            # Нам нужен кастомный класс диалекта для последующего сохранения с тем же разделителем
            class CustomDialect(csv.excel):
                delimiter = d
            self.csv_dialect = CustomDialect
            
            # Обновляем статусбар
            self.lbl_status.config(
                text=f"Файл: {os.path.basename(file_path)} | Строк: {len(self.data)} | Разделитель: {repr(delimiter)}"
            )
            self.btn_change_col.pack(side="right", padx=5)
            
            # Открываем окно выбора колонки
            self.choose_kanban_column()

        except Exception as e:
            messagebox.showerror("Ошибка парсинга CSV", f"Не удалось прочитать структуру файла:\n{str(e)}")

    def choose_kanban_column(self):
        # Окно выбора колонки для построения доски
        win = tk.Toplevel(self)
        win.title("Выбор колонки")
        win.geometry("300x150")
        win.transient(self)
        win.grab_set()

        ttk.Label(
            win, text="Выберите колонку для Канбан-доски:", padding=10
        ).pack()
        combo = ttk.Combobox(win, values=self.headers, state="readonly")
        combo.pack(padx=10, pady=5, fill="x")
        if self.headers:
            combo.current(0)

        def confirm():
            self.kanban_column = combo.get()
            win.destroy()
            self.build_board()

        ttk.Button(win, text="ОК", command=confirm).pack(pady=10)

    def build_board(self):
        # Очищаем старую доску
        for child in self.board_frame.winfo_children():
            child.destroy()

        if not self.kanban_column:
            return

        # Находим все уникальные значения для колонок доски
        unique_values = sorted(
            list(set(str(row.get(self.kanban_column, "")).strip() for row in self.data))
        )
        if "" not in unique_values:
            unique_values.append("")  # Для записей с пустым значением

        # Создаем столбцы
        for col_idx, col_value in enumerate(unique_values):
            col_title = col_value if col_value else "[Пусто]"

            # Фрейм колонки
            col_frame = ttk.LabelFrame(
                self.board_frame, text=f" {col_title} ", padding=5
            )
            col_frame.grid(row=0, column=col_idx, padx=10, py=10, sticky="nws")

            # Внутренний контейнер для карточек (чтобы задать ширину)
            cards_container = ttk.Frame(col_frame, width=250)
            cards_container.pack(fill="both", expand=True)
            cards_container.pack_propagate(False)

            # Пересобираем контейнер под контент, если он длинный (динамический ресайз высоты)
            cards_container.config(
                width=260, height=600
            )  # Фиксированная ширина доски

            # Заполняем карточками
            for row_idx, row_dict in enumerate(self.data):
                val = str(row_dict.get(self.kanban_column, "")).strip()
                if val == col_value:
                    self.create_card(cards_container, row_dict)

    def create_card(self, parent, row_dict):
        # Создаем визуальную карточку
        card = tk.Frame(
            parent, bg="#ffffff", bd=1, relief="solid", cursor="hand2"
        )
        card.pack(fill="x", padx=5, pady=5)

        # Текстовое превью полей внутри карточки
        preview_text = ""
        # Показываем первые 3 поля для компактности
        for h in self.headers[:4]:
            val = row_dict.get(h, "")
            # Обрезаем слишком длинный текст
            val_trunc = val[:25] + "..." if len(val) > 25 else val
            preview_text += f"• {h}: {val_trunc}\n"

        lbl = tk.Label(
            card,
            text=preview_text,
            bg="#ffffff",
            justify="left",
            anchor="w",
            font=("Arial", 9),
            padx=5,
            py=5,
        )
        lbl.pack(fill="both", expand=True)

        # Биндим двойной клик на открытие редактирования
        def on_double_click(event, r=row_dict):
            self.edit_row(r)

        card.bind("<Double-1>", on_double_click)
        lbl.bind("<Double-1>", on_double_click)

    def edit_row(self, row_dict):
        dialog = EditCardDialog(self, row_dict, self.headers)
        self.wait_window(dialog)

        if dialog.result:
            # Обновляем данные в памяти
            row_dict.update(dialog.result)
            # Перестраиваем доску, так как значения (включая ключевое) могли измениться
            self.build_board()

    def save_file(self):
        if not self.file_path:
            messagebox.showwarning(
                "Внимание", "Нет открытого файла для сохранения."
            )
            return

        try:
            # Перезаписываем файл, строго соблюдая исходный диалект
            with open(self.file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=self.headers, dialect=self.csv_dialect
                )
                writer.writeheader()
                writer.writerows(self.data)

            messagebox.showinfo(
                "Успех", "Файл успешно сохранен с исходной структурой!"
            )
        except Exception as e:
            messagebox.showerror(
                "Ошибка сохранения", f"Не удалось сохранить файл:\n{str(e)}"
            )


if __name__ == "__main__":
    app = KanbanCSVApp()
    app.mainloop()
