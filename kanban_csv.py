import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# --- Конфигурация темы и цвета ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")  # Стандартная синяя тема (ACCENT_COLOR)

BG_MAIN = "#1e1e1e"
BG_PANEL = "#252526"
BG_CARD = "#2d2d30"
FG_TEXT = "#e1e1e1"
FG_MUTED = "#858585"
BORDER_COLOR = "#3f3f46"

PAGE_SIZE = 25


class EditCardDialog(ctk.CTkToplevel):

    def __init__(self, parent, row_data, headers, text_column=None, is_new=False):
        super().__init__(parent)
        self.title("Новая запись" if is_new else "Редактирование записи")
        self.configure(fg_color=BG_MAIN)
        
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self.headers = headers
        self.text_column = text_column
        self.result = None

        # Нижняя панель действий
        btn_frame = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0)
        btn_frame.pack(fill="x", side="bottom", ipady=13)

        cancel_btn = ctk.CTkButton(
            btn_frame, text="Отмена", command=self.destroy, font=("Arial", 15),
            fg_color=BG_CARD, text_color=FG_TEXT, hover_color=BORDER_COLOR,
            width=110, height=40
        )
        cancel_btn.pack(side="right", padx=18)

        save_btn = ctk.CTkButton(
            btn_frame, text="Сохранить", command=self.save, font=("Arial", 15, "bold"),
            fg_color="#007acc", text_color="white", hover_color="#0062a3",
            width=130, height=40
        )
        save_btn.pack(side="right", padx=6)

        # Современный скролл-контейнер контента
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self, fg_color=BG_MAIN, corner_radius=0
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=12, pady=12)

        self.widgets = {}
        for header in self.headers:
            frame = ctk.CTkFrame(self.scrollable_frame, fg_color=BG_MAIN)
            frame.pack(fill="x", pady=8, padx=6)

            lbl = ctk.CTkLabel(frame, text=header, font=("Arial", 14, "bold"), text_color=FG_TEXT)
            lbl.pack(anchor="w")

            if text_column and header == text_column:
                text_area = ctk.CTkTextbox(
                    frame, font=("Arial", 15), fg_color=BG_CARD, text_color=FG_TEXT,
                    border_color=BORDER_COLOR, border_width=1, height=140, wrap="word",
                    activate_scrollbars=True
                )
                text_area.insert("1.0", str(row_data.get(header, "")))
                text_area.pack(fill="x", pady=5)
                self.widgets[header] = text_area
            else:
                entry = ctk.CTkEntry(
                    frame, font=("Arial", 15), fg_color=BG_CARD, text_color=FG_TEXT,
                    border_color=BORDER_COLOR, border_width=1, height=40
                )
                entry.insert(0, str(row_data.get(header, "")))
                entry.pack(fill="x", pady=5)
                self.widgets[header] = entry

        self.initial_geometry(parent)

    def initial_geometry(self, parent):
        self.update_idletasks()
        width, height = 800, 850
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def save(self):
        self.result = {}
        for h in self.headers:
            w = self.widgets[h]
            if isinstance(w, ctk.CTkTextbox):
                self.result[h] = w.get("1.0", "end-1c").strip()
            else:
                self.result[h] = w.get().strip()
        self.grab_release()
        self.destroy()


class KanbanCSVApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("CSV Kanban Editor")
        self.configure(fg_color=BG_MAIN)

        self.file_path = None
        self.headers = []
        self.data = []
        self.csv_dialect = None
        self.kanban_column = None
        self.text_column = None
        
        self.column_pages = {}
        self.column_data_map = {}

        self.init_main_ui()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width, height = 1850, 1000
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def init_main_ui(self):
        # Верхняя панель управления
        self.top_bar = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=60)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)

        self.btn_open = ctk.CTkButton(
            self.top_bar, text="Открыть CSV (Ctrl+O)", command=self.open_file, font=("Arial", 14),
            fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1,
            hover_color=BORDER_COLOR, width=180, height=40
        )
        self.btn_open.pack(side="left", padx=10, pady=10)

        self.btn_save = ctk.CTkButton(
            self.top_bar, text="Сохранить (Ctrl+S)", command=self.save_file, font=("Arial", 14),
            fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1,
            hover_color=BORDER_COLOR, width=180, height=40
        )
        self.btn_save.pack(side="left", padx=5, pady=10)

        self.btn_change_col = ctk.CTkButton(
            self.top_bar, text="Настройка колонок", command=self.setup_kanban_columns_dialog, font=("Arial", 14),
            fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1,
            hover_color=BORDER_COLOR, width=180, height=40
        )
        
        self.btn_add_card = ctk.CTkButton(
            self.top_bar, text="+ Добавить запись", command=self.add_new_card, font=("Arial", 14, "bold"),
            fg_color="#007acc", text_color="white", hover_color="#0062a3", width=180, height=40
        )

        self.lbl_status = ctk.CTkLabel(self.top_bar, text="Файл не загружен.", font=("Arial", 14, "italic"), text_color=FG_TEXT)
        self.lbl_status.pack(side="left", padx=20)

        self.main_container = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

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
            
            self.lbl_status.configure(text=f"Файл: {os.path.basename(file_path)} | Строк: {len(self.data)}")
            
            self.btn_change_col.pack(side="right", padx=10, pady=10)
            self.btn_add_card.pack(side="right", padx=5, pady=10)
            
            self.setup_kanban_columns_dialog()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{str(e)}")

    def setup_kanban_columns_dialog(self):
        win = ctk.CTkToplevel(self)
        win.title("Конфигурация доски")
        win.configure(fg_color=BG_MAIN)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        
        ctk.CTkLabel(win, text="Группировать по колонке:", font=("Arial", 14, "bold"), text_color=FG_TEXT).pack(pady=(20, 4), padx=25, anchor="w")
        combo_kanban = ctk.CTkComboBox(win, values=self.headers, state="readonly", font=("Arial", 15), dropdown_font=("Arial", 15), height=40)
        combo_kanban.pack(padx=25, pady=6, fill="x")
        combo_kanban.set(self.kanban_column if self.kanban_column in self.headers else self.headers[0])

        ctk.CTkLabel(win, text="Поле многострочного текста (Textarea):", font=("Arial", 14, "bold"), text_color=FG_TEXT).pack(pady=(20, 4), padx=25, anchor="w")
        combo_text = ctk.CTkComboBox(win, values=["[Нет]"] + self.headers, state="readonly", font=("Arial", 15), dropdown_font=("Arial", 15), height=40)
        combo_text.pack(padx=25, pady=6, fill="x")
        combo_text.set(self.text_column if self.text_column in self.headers else "[Нет]")

        def confirm():
            self.kanban_column = combo_kanban.get()
            selected_txt = combo_text.get()
            self.text_column = None if selected_txt == "[Нет]" else selected_txt
            win.grab_release()
            win.destroy()
            self.build_board()

        ctk.CTkButton(
            win, text="Построить доску", command=confirm, fg_color="#007acc", text_color="white",
            hover_color="#0062a3", font=("Arial", 14, "bold"), height=45
        ).pack(pady=25, padx=25, fill="x")
        
        win.update_idletasks()
        w, h = 500, 340
        x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

    def build_board(self):
        for child in self.main_container.winfo_children():
            child.destroy()

        if not self.kanban_column:
            return

        self.column_data_map = {}
        for row in self.data:
            val = str(row.get(self.kanban_column, "")).strip()
            if val not in self.column_data_map:
                self.column_data_map[val] = []
            self.column_data_map[val].append(row)

        sorted_values = sorted(list(self.column_data_map.keys()))
        num_columns = len(sorted_values)

        for col_idx in range(num_columns):
            self.main_container.grid_columnconfigure(col_idx, weight=1, uniform="group1")
        self.main_container.grid_rowconfigure(0, weight=1)

        for col_idx, col_value in enumerate(sorted_values):
            col_title = col_value if col_value else "[Пусто]"
            rows_in_col = self.column_data_map[col_value]

            col_frame = ctk.CTkFrame(self.main_container, fg_color=BG_PANEL, border_color=BORDER_COLOR, border_width=1)
            col_frame.grid(row=0, column=col_idx, padx=5, pady=5, sticky="nsew")

            col_header = ctk.CTkLabel(col_frame, text=f"{col_title.upper()} ({len(rows_in_col)})", font=("Arial", 14, "bold"), text_color=FG_TEXT)
            col_header.pack(fill="x", pady=12)

            # Нативный ленивый скролл фрейм CustomTkinter
            scroll_cards_frame = ctk.CTkScrollableFrame(col_frame, fg_color=BG_PANEL, corner_radius=0)
            scroll_cards_frame.pack(fill="both", expand=True, padx=2, pady=2)

            self.column_pages[col_value] = PAGE_SIZE

            # Обработчик скролла для подгрузки данных
            def make_scroll_listener(val=col_value, frame=scroll_cards_frame):
                def check_scroll(event=None):
                    # Отслеживаем положение ползунка встроенного canvas
                    if hasattr(frame, "_canvas"):
                        y_view = frame._canvas.yview()
                        if y_view[1] >= 0.9:
                            self.load_more_cards(val, frame)
                return check_scroll

            scroll_listener = make_scroll_listener()
            if hasattr(scroll_cards_frame, "_canvas"):
                scroll_cards_frame._canvas.bind("<MouseWheel>", lambda e, sl=scroll_listener: [scroll_cards_frame._on_mousewheel(e), sl()], add="+")

            self.render_cards_chunk(col_value, scroll_cards_frame, 0, PAGE_SIZE)

    def render_cards_chunk(self, col_value, target_frame, start_idx, end_idx):
        rows = self.column_data_map[col_value]
        chunk = rows[start_idx:end_idx]

        if start_idx == 0 and not chunk:
            placeholder = ctk.CTkLabel(target_frame, text="(Нет записей)", font=("Arial", 14, "italic"), text_color=FG_MUTED)
            placeholder.pack(fill="x", pady=20)
            return

        for row_dict in chunk:
            card = ctk.CTkFrame(target_frame, fg_color=BG_CARD, border_color=BORDER_COLOR, border_width=1, cursor="hand2")
            card.pack(fill="x", padx=8, pady=6, anchor="n")

            preview_text = ""
            for h in self.headers[:4]:
                val = str(row_dict.get(h, ""))
                val_trunc = val[:45] + "..." if len(val) > 45 else val
                preview_text += f"• {h}: {val_trunc}\n"

            lbl = ctk.CTkLabel(
                card, text=preview_text.strip(), font=("Arial", 13), text_color=FG_TEXT,
                justify="left", anchor="w", wraplength=330
            )
            lbl.pack(fill="both", expand=True, padx=12, pady=12)

            card.bind("<Configure>", lambda e, l=lbl: l.configure(wraplength=max(150, e.width - 24)))

            def make_click_handler(r=row_dict):
                return lambda e: self.edit_row(r)

            card.bind("<Double-1>", make_click_handler())
            lbl.bind("<Double-1>", make_click_handler())

    def load_more_cards(self, col_value, target_frame):
        current_limit = self.column_pages[col_value]
        total_rows = len(self.column_data_map[col_value])
        
        if current_limit >= total_rows:
            return

        next_limit = current_limit + PAGE_SIZE
        self.column_pages[col_value] = next_limit
        
        self.render_cards_chunk(col_value, target_frame, current_limit, next_limit)

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
            self.lbl_status.configure(text=f"Файл: {os.path.basename(self.file_path)} | Строк: {len(self.data)}")
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
