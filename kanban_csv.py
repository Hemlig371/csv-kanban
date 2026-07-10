import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class EditCardDialog(tk.Toplevel):

    def __init__(self, parent, row_data, headers):
        super().__init__(parent)
        self.title("Редактирование записи")
        self.geometry("450x550")
        self.transient(parent)
        self.grab_set()

        self.headers = headers
        self.result = None

        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")

        self.entries = {}
        for header in self.headers:
            frame = ttk.Frame(self.scrollable_frame)
            frame.pack(fill="x", pady=5, padx=5)

            lbl = ttk.Label(frame, text=header, font=("Arial", 10, "bold"))
            lbl.pack(anchor="w")

            entry = ttk.Entry(frame, width=45)
            entry.insert(0, str(row_data.get(header, "")))
            entry.pack(fill="x", pady=2)
            self.entries[header] = entry

        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill="x", side="bottom")

        ttk.Button(btn_frame, text="Отмена", command=self.destroy).pack(
            side="right", padx=5
        )
        ttk.Button(btn_frame, text="Сохранить", command=self.save).pack(
            side="right"
        )

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

        self.file_path = None
        self.headers = []
        self.data = []
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
        self.top_bar = ttk.Frame(self, padding=10, relief="groove")
        self.top_bar.pack(fill="x", side="top")

        self.lbl_status = ttk.Label(
            self.top_bar,
            text="Файл не выбран. Откройте CSV через Файл -> Открыть (Ctrl+O)",
            font=("Arial", 10, "italic"),
        )
        self.lbl_status.pack(side="left")

        self.btn_change_col = ttk.Button(
            self.top_bar, text="Сменить колонку доски", command=self.choose_kanban_column
        )

        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True, padx=5, pady=5)

        self.board_canvas = tk.Canvas(self.main_container, borderwidth=0, highlightthickness=0)
        self.h_scrollbar = ttk.Scrollbar(
            self.main_container, orient="horizontal", command=self.board_canvas.xview
        )
        self.v_scrollbar = ttk.Scrollbar(
            self.main_container, orient="vertical", command=self.board_canvas.yview
        )

        self.board_frame = ttk.Frame(self.board_canvas)
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
            self.btn_change_col.pack(side="right", padx=5)
            
            self.choose_kanban_column()

        except Exception as e:
            messagebox.showerror("Ошибка парсинга CSV", f"Не удалось прочитать структуру файла:\n{str(e)}")

    def choose_kanban_column(self):
        win = tk.Toplevel(self)
        win.title("Выбор колонки")
        win.geometry("350x160")
        win.transient(self)
        win.grab_set()

        ttk.Label(
            win, text="Выберите колонку для Канбан-доски:", padding=10, justify="center"
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

        ttk.Button(win, text="Построить доску", command=confirm).pack(pady=15)
        
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

            col_frame = ttk.LabelFrame(
                self.board_frame, text=f" {col_title} ", padding=8
            )
            # ИСПРАВЛЕНО: замещено py=8 на pady=8
            col_frame.grid(row=0, column=col_idx, padx=8, pady=8, sticky="nsew")

            cards_frame = ttk.Frame(col_frame)
            cards_frame.pack(fill="both", expand=True)

            has_cards = False
            for row_dict in self.data:
                val = str(row_dict.get(self.kanban_column, "")).strip()
                if val == col_value:
                    self.create_card(cards_frame, row_dict)
                    has_cards = True
            
            col_frame.config(width=280)
            if not has_cards:
                placeholder = ttk.Label(cards_frame, text="(Нет записей)", foreground="gray", padding=10)
                placeholder.pack()

        self.update_idletasks()
        self.board_canvas.configure(scrollregion=self.board_canvas.bbox("all"))

    def create_card(self, parent, row_dict):
        card = tk.Frame(
            parent, bg="#ffffff", bd=1, relief="solid", cursor="hand2"
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
            bg="#ffffff",
            justify="left",
            anchor="w",
            font=("Arial", 9),
            padx=6,
            pady=6,
            wraplength=240
        )
        lbl.pack(fill="both", expand=True)

        def on_double_click(event, r=row_dict):
            self.edit_row(r)

        card.bind("<Double-1>", on_double_click)
        lbl.bind("<Double-1>", on_double_click)

    def edit_row(self, row_dict):
        dialog = EditCardDialog(self, row_dict, self.headers)
        self.wait_window(dialog)

        if dialog.result:
            row_dict.update(dialog.result)
            self.build_board()

    def save_file(self):
        if not self.file_path:
            messagebox.showwarning(
                "Внимание", "Нет открытого файла для сохранения."
            )
            return

        try:
            with open(self.file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(
                    f, fieldnames=self.headers, dialect=self.csv_dialect
                )
                writer.writeheader()
                writer.writerows(self.data)

            messagebox.showinfo(
                "Успех", "Файл успешно сохранен!"
            )
        except Exception as e:
            messagebox.showerror(
                "Ошибка сохранения", f"Не удалось сохранить файл:\n{str(e)}"
            )


if __name__ == "__main__":
    app = KanbanCSVApp()
    app.mainloop()
