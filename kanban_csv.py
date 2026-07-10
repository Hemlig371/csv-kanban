import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# --- Конфигурация темы и цвета ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_MAIN = "#1e1e1e"
BG_PANEL = "#252526"
BG_CARD = "#2d2d30"
FG_TEXT = "#e1e1e1"
FG_MUTED = "#858585"
BORDER_COLOR = "#3f3f46"

PAGE_SIZE = 25

# --- Пропорционально увеличенные шрифты (~15%) ---
FONT_TITLE = ("Arial", 18, "bold")
FONT_HEADER = ("Arial", 16, "bold")
FONT_TEXT_BOLD = ("Arial", 15, "bold")
FONT_MAIN = ("Arial", 16)
FONT_CARD = ("Arial", 15)
FONT_MUTED_ITALIC = ("Arial", 16, "italic")


class KanbanCSVApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("CSV Kanban Editor Pro")
        self.configure(fg_color=BG_MAIN)

        # Реестр сессий вкладок
        self.tabs_data = {}
        self.active_tab = None

        self.init_main_ui()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width, height = 1850, 1000
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def init_main_ui(self):
        # --- Верхняя панель ---
        self.top_bar = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=65)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)

        self.btn_open = ctk.CTkButton(
            self.top_bar, text="Открыть CSV (Ctrl+O)", command=self.open_file, font=FONT_MAIN,
            fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1,
            hover_color=BORDER_COLOR, width=190, height=45
        )
        self.btn_open.pack(side="left", padx=10, pady=10)

        self.btn_save = ctk.CTkButton(
            self.top_bar, text="Сохранить (Ctrl+S)", command=self.save_file, font=FONT_MAIN,
            fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1,
            hover_color=BORDER_COLOR, width=190, height=45
        )
        self.btn_save.pack(side="left", padx=5, pady=10)

        self.btn_change_col = ctk.CTkButton(
            self.top_bar, text="Настройка колонок", command=self.setup_kanban_columns_dialog, font=FONT_MAIN,
            fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1,
            hover_color=BORDER_COLOR, width=190, height=45
        )
        
        self.btn_add_card = ctk.CTkButton(
            self.top_bar, text="+ Добавить запись", command=self.add_new_card, font=FONT_TEXT_BOLD,
            fg_color="#007acc", text_color="white", hover_color="#0062a3", width=190, height=45
        )

        self.lbl_status = ctk.CTkLabel(self.top_bar, text="Файлы не загружены.", font=FONT_MUTED_ITALIC, text_color=FG_TEXT)
        self.lbl_status.pack(side="left", padx=20)

        self.btn_close_tab = ctk.CTkButton(
            self.top_bar, text="Закрыть вкладку ✕", command=self.close_current_tab, font=FONT_MAIN,
            fg_color="#a83232", text_color="white", hover_color="#822525", width=160, height=40
        )

        # --- Рабочая область (Разделение на Доску и Редактор) ---
        self.work_area = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.work_area.pack(fill="both", expand=True, padx=5, pady=5)

        # Правая часть — Фиксированный монолитный редактор
        self.right_editor_frame = ctk.CTkFrame(self.work_area, fg_color=BG_PANEL, width=520, border_color=BORDER_COLOR, border_width=1, corner_radius=8)
        self.right_editor_frame.pack(side="right", fill="y", padx=5, pady=5)
        self.right_editor_frame.pack_propagate(False)

        # Левая часть — Пространство под доски
        self.left_frame = ctk.CTkFrame(self.work_area, fg_color=BG_MAIN, corner_radius=0)
        self.left_frame.pack(side="left", fill="both", expand=True)

        self.tab_control = ctk.CTkTabview(self.left_frame, fg_color=BG_MAIN, command=self.on_tab_changed)
        # Увеличиваем шрифт самих вкладок сверху
        self.tab_control._segmented_button.configure(font=FONT_MAIN)
        self.tab_control.pack(fill="both", expand=True)

        self.editor_content_scroll = None
        self.editor_widgets = {}
        self.current_editing_row = None
        self.is_creating_new_card = False

        self.show_editor_placeholder()

        self.bind_all("<Control-o>", lambda e: self.open_file())
        self.bind_all("<Control-s>", lambda e: self.save_file())

    # --- Управление вкладками ---

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not file_path: return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [f.readline() for _ in range(5)]
            if not lines: raise ValueError("Файл пустой.")

            detected_delimiter = ';' if ';' in lines[0] else (',' if ',' in lines[0] else '\t')

            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=detected_delimiter)
                headers = reader.fieldnames
                data = list(reader)

            if not headers: raise ValueError("Не удалось определить структуру CSV.")

            tab_title = os.path.basename(file_path)
            base_title = tab_title
            counter = 1
            while tab_title in self.tabs_data:
                tab_title = f"{base_title} ({counter})"
                counter += 1

            class CustomDialect(csv.excel): delimiter = detected_delimiter

            self.tabs_data[tab_title] = {
                "file_path": file_path,
                "headers": headers,
                "data": data,
                "csv_dialect": CustomDialect,
                "kanban_column": None,
                "text_column": None,
                "column_pages": {},
                "column_data_map": {}
            }

            self.tab_control.add(tab_title)
            
            tab_scroll = ctk.CTkScrollableFrame(self.tab_control.tab(tab_title), fg_color=BG_MAIN, corner_radius=0, orientation="horizontal")
            tab_scroll.pack(fill="both", expand=True)
            
            tab_container = ctk.CTkFrame(tab_scroll, fg_color=BG_MAIN, corner_radius=0)
            tab_container.pack(fill="both", expand=True)
            
            self.tabs_data[tab_title]["container"] = tab_container
            self.tabs_data[tab_title]["scroll_root"] = tab_scroll

            self.tab_control.set(tab_title)
            self.on_tab_changed()
            self.setup_kanban_columns_dialog()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{str(e)}")

    def on_tab_changed(self):
        self.active_tab = self.tab_control.get()
        if not self.active_tab or self.active_tab not in self.tabs_data:
            self.active_tab = None
            self.lbl_status.configure(text="Файлы не загружены.")
            self.btn_change_col.pack_forget()
            self.btn_add_card.pack_forget()
            self.btn_close_tab.pack_forget()
            self.show_editor_placeholder()
            return

        t_data = self.tabs_data[self.active_tab]
        self.lbl_status.configure(text=f"Файл: {os.path.basename(t_data['file_path'])} | Строк: {len(t_data['data'])}")
        
        self.btn_change_col.pack(side="right", padx=10, pady=10)
        self.btn_add_card.pack(side="right", padx=5, pady=10)
        self.btn_close_tab.pack(side="right", padx=10, pady=10)
        
        self.show_editor_placeholder()

    def close_current_tab(self):
        if not self.active_tab: return
        target_to_close = self.active_tab
        
        if messagebox.askyesno("Закрыть вкладку", f"Вы уверены, что хотите закрыть вкладку '{target_to_close}'?\nНесохраненные изменения будут потеряны."):
            self.tab_control.delete(target_to_close)
            del self.tabs_data[target_to_close]
            self.on_tab_changed()

    def setup_kanban_columns_dialog(self):
        if not self.active_tab: return
        t_data = self.tabs_data[self.active_tab]

        win = ctk.CTkToplevel(self)
        win.title("Конфигурация доски")
        win.configure(fg_color=BG_MAIN)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        
        ctk.CTkLabel(win, text="Группировать по колонке:", font=FONT_HEADER, text_color=FG_TEXT).pack(pady=(20, 4), padx=25, anchor="w")
        combo_kanban = ctk.CTkComboBox(win, values=t_data["headers"], state="readonly", font=FONT_MAIN, dropdown_font=FONT_MAIN, height=45)
        combo_kanban.pack(padx=25, pady=6, fill="x")
        combo_kanban.set(t_data["kanban_column"] if t_data["kanban_column"] in t_data["headers"] else t_data["headers"][0])

        ctk.CTkLabel(win, text="Поле многострочного текста (Textarea):", font=FONT_HEADER, text_color=FG_TEXT).pack(pady=(20, 4), padx=25, anchor="w")
        combo_text = ctk.CTkComboBox(win, values=["[Нет]"] + t_data["headers"], state="readonly", font=FONT_MAIN, dropdown_font=FONT_MAIN, height=45)
        combo_text.pack(padx=25, pady=6, fill="x")
        combo_text.set(t_data["text_column"] if t_data["text_column"] in t_data["headers"] else "[Нет]")

        def confirm():
            t_data["kanban_column"] = combo_kanban.get()
            selected_txt = combo_text.get()
            t_data["text_column"] = None if selected_txt == "[Нет]" else selected_txt
            win.grab_release()
            win.destroy()
            self.build_board()

        ctk.CTkButton(
            win, text="Построить доску", command=confirm, fg_color="#007acc", text_color="white",
            hover_color="#0062a3", font=FONT_TEXT_BOLD, height=50
        ).pack(pady=25, padx=25, fill="x")
        
        win.update_idletasks()
        w, h = 520, 360
        x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{max(0, x)}+{max(0, y)}")

    # --- Логика Канбан-доски ---

    def build_board(self):
        if not self.active_tab: return
        t_data = self.tabs_data[self.active_tab]
        container = t_data["container"]

        for child in container.winfo_children():
            child.destroy()

        if not t_data["kanban_column"]: return

        t_data["column_data_map"] = {}
        for row in t_data["data"]:
            val = str(row.get(t_data["kanban_column"], "")).strip()
            t_data["column_data_map"].setdefault(val, []).append(row)

        sorted_values = sorted(list(t_data["column_data_map"].keys()))
        num_columns = len(sorted_values)

        for col_idx in range(num_columns):
            container.grid_columnconfigure(col_idx, weight=0, minsize=380)
        container.grid_rowconfigure(0, weight=1)

        for col_idx, col_value in enumerate(sorted_values):
            col_title = col_value if col_value else "[Пусто]"
            rows_in_col = t_data["column_data_map"][col_value]

            col_frame = ctk.CTkFrame(container, fg_color=BG_PANEL, border_color=BORDER_COLOR, border_width=1, width=370)
            col_frame.grid(row=0, column=col_idx, padx=6, pady=5, sticky="nsew")
            col_frame.pack_propagate(False)

            col_header = ctk.CTkLabel(col_frame, text=f"{col_title.upper()} ({len(rows_in_col)})", font=FONT_HEADER, text_color=FG_TEXT)
            col_header.pack(fill="x", pady=14)

            scroll_cards_frame = ctk.CTkScrollableFrame(col_frame, fg_color=BG_PANEL, corner_radius=0)
            scroll_cards_frame.pack(fill="both", expand=True, padx=2, pady=2)

            if hasattr(scroll_cards_frame, "_scrollbar"):
                scroll_cards_frame._scrollbar.pack_forget()

            t_data["column_pages"][col_value] = PAGE_SIZE

            def make_scroll_listener(val=col_value, frame=scroll_cards_frame):
                def check_scroll(event=None):
                    if hasattr(frame, "_canvas"):
                        y_view = frame._canvas.yview()
                        if y_view[1] >= 0.9:
                            self.load_more_cards(val, frame)
                        if y_view[0] == 0.0 and y_view[1] == 1.0:
                            frame._scrollbar.pack_forget()
                        else:
                            frame._scrollbar.pack(side="right", fill="y")
                return check_scroll

            scroll_listener = make_scroll_listener()
            if hasattr(scroll_cards_frame, "_canvas"):
                scroll_cards_frame._canvas.bind("<MouseWheel>", lambda e, sl=scroll_listener: [scroll_cards_frame._on_mousewheel(e), sl()], add="+")

            self.render_cards_chunk(col_value, scroll_cards_frame, 0, PAGE_SIZE)

    def render_cards_chunk(self, col_value, target_frame, start_idx, end_idx):
        t_data = self.tabs_data[self.active_tab]
        rows = t_data["column_data_map"][col_value]
        chunk = rows[start_idx:end_idx]

        if start_idx == 0 and not chunk:
            placeholder = ctk.CTkLabel(target_frame, text="(Нет записей)", font=FONT_MUTED_ITALIC, text_color=FG_MUTED)
            placeholder.pack(fill="x", pady=20)
            return

        for row_dict in chunk:
            card = ctk.CTkFrame(target_frame, fg_color=BG_CARD, border_color=BORDER_COLOR, border_width=1, cursor="hand2")
            card.pack(fill="x", padx=8, pady=6, anchor="n")

            preview_text = ""
            for h in t_data["headers"][:4]:
                val = str(row_dict.get(h, ""))
                val_trunc = val[:45] + "..." if len(val) > 45 else val
                preview_text += f"• {h}: {val_trunc}\n"

            lbl = ctk.CTkLabel(
                card, text=preview_text.strip(), font=FONT_CARD, text_color=FG_TEXT,
                justify="left", anchor="w", wraplength=330
            )
            lbl.pack(fill="both", expand=True, padx=12, pady=12)

            def make_click_handler(r=row_dict):
                return lambda e: self.load_row_into_editor(r)

            card.bind("<Double-1>", make_click_handler())
            lbl.bind("<Double-1>", make_click_handler())
            
        self.after(200, lambda: self.toggle_scrollbar_visibility(target_frame))

    def toggle_scrollbar_visibility(self, frame):
        if hasattr(frame, "_canvas") and hasattr(frame, "_scrollbar"):
            frame._canvas.update_idletasks()
            y_view = frame._canvas.yview()
            if y_view[0] == 0.0 and y_view[1] == 1.0:
                frame._scrollbar.pack_forget()
            else:
                frame._scrollbar.pack(side="right", fill="y")

    def load_more_cards(self, col_value, target_frame):
        t_data = self.tabs_data[self.active_tab]
        current_limit = t_data["column_pages"][col_value]
        total_rows = len(t_data["column_data_map"][col_value])
        
        if current_limit >= total_rows: return

        next_limit = current_limit + PAGE_SIZE
        t_data["column_pages"][col_value] = next_limit
        
        self.render_cards_chunk(col_value, target_frame, current_limit, next_limit)

    # --- Боковая панель редактирования ---

    def show_editor_placeholder(self):
        for child in self.right_editor_frame.winfo_children():
            child.destroy()
        self.current_editing_row = None
        self.is_creating_new_card = False
        
        placeholder = ctk.CTkLabel(self.right_editor_frame, text="", fg_color=BG_PANEL)
        placeholder.pack(fill="both", expand=True)

    def load_row_into_editor(self, row_dict, is_new=False):
        for child in self.right_editor_frame.winfo_children():
            child.destroy()

        self.current_editing_row = row_dict
        self.is_creating_new_card = is_new
        t_data = self.tabs_data[self.active_tab]

        title_lbl = ctk.CTkLabel(
            self.right_editor_frame, text="Новая запись" if is_new else "Редактирование",
            font=FONT_TITLE, text_color=FG_TEXT, fg_color=BG_PANEL, height=45
        )
        title_lbl.pack(fill="x", side="top", pady=(10, 0))

        btn_frame = ctk.CTkFrame(self.right_editor_frame, fg_color=BG_PANEL, corner_radius=0)
        btn_frame.pack(fill="x", side="bottom", pady=20)

        cancel_btn = ctk.CTkButton(
            btn_frame, text="Отмена", command=self.show_editor_placeholder, font=FONT_MAIN,
            fg_color=BG_CARD, text_color=FG_TEXT, hover_color=BORDER_COLOR, width=120, height=40
        )
        cancel_btn.pack(side="right", padx=15)

        save_btn = ctk.CTkButton(
            btn_frame, text="Сохранить", command=self.save_editor_data, font=FONT_TEXT_BOLD,
            fg_color="#007acc", text_color="white", hover_color="#0062a3", width=130, height=40
        )
        save_btn.pack(side="right", padx=0)

        self.editor_content_scroll = ctk.CTkScrollableFrame(self.right_editor_frame, fg_color=BG_PANEL, corner_radius=0)
        self.editor_content_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self.editor_widgets = {}
        existing_statuses = sorted(list(set(str(r.get(t_data["kanban_column"], "")).strip() for r in t_data["data"] if r.get(t_data["kanban_column"], ""))))

        for header in t_data["headers"]:
            frame = ctk.CTkFrame(self.editor_content_scroll, fg_color=BG_PANEL)
            frame.pack(fill="x", pady=8, padx=4)

            lbl = ctk.CTkLabel(frame, text=header, font=FONT_HEADER, text_color=FG_TEXT)
            lbl.pack(anchor="w", pady=(0, 4))

            if header == t_data["kanban_column"]:
                combo = ctk.CTkComboBox(
                    frame, values=[""] + existing_statuses, state="normal", font=FONT_MAIN,
                    dropdown_font=FONT_MAIN, fg_color=BG_CARD, border_color=BORDER_COLOR, height=42
                )
                if is_new:
                    combo.set("")
                else:
                    combo.set(str(row_dict.get(header, "")))
                combo.pack(fill="x", pady=4)
                self.editor_widgets[header] = combo

            elif t_data["text_column"] and header == t_data["text_column"]:
                text_area = ctk.CTkTextbox(
                    frame, font=FONT_MAIN, fg_color=BG_CARD, text_color=FG_TEXT,
                    border_color=BORDER_COLOR, border_width=1, height=180, wrap="word"
                )
                text_area.insert("1.0", str(row_dict.get(header, "")))
                text_area.pack(fill="x", pady=4)
                self.editor_widgets[header] = text_area

            else:
                entry = ctk.CTkEntry(
                    frame, font=FONT_MAIN, fg_color=BG_CARD, text_color=FG_TEXT,
                    border_color=BORDER_COLOR, border_width=1, height=42
                )
                entry.insert(0, str(row_dict.get(header, "")))
                entry.pack(fill="x", pady=4)
                self.editor_widgets[header] = entry

    def save_editor_data(self):
        if not self.active_tab or not self.current_editing_row: return
        t_data = self.tabs_data[self.active_tab]

        result = {}
        for h in t_data["headers"]:
            w = self.editor_widgets[h]
            if isinstance(w, ctk.CTkTextbox):
                result[h] = w.get("1.0", "end-1c").strip()
            else:
                result[h] = w.get().strip()

        if not result.get(t_data["kanban_column"]):
            messagebox.showwarning("Внимание", f"Поле группировки '{t_data['kanban_column']}' не может быть пустым при сохранении!")
            return

        self.current_editing_row.update(result)

        if self.is_creating_new_card:
            t_data["data"].append(self.current_editing_row)
            self.lbl_status.configure(text=f"Файл: {os.path.basename(t_data['file_path'])} | Строк: {len(t_data['data'])}")

        self.build_board()
        self.show_editor_placeholder()

    def add_new_card(self):
        if not self.active_tab: return
        t_data = self.tabs_data[self.active_tab]
        
        new_row = {h: "" for h in t_data["headers"]}
        self.load_row_into_editor(new_row, is_new=True)

    def save_file(self):
        if not self.active_tab: return
        t_data = self.tabs_data[self.active_tab]
        try:
            with open(t_data["file_path"], "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=t_data["headers"], dialect=t_data["csv_dialect"])
                writer.writeheader()
                writer.writerows(t_data["data"])
            messagebox.showinfo("Успех", "Файл успешно сохранен!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{str(e)}")


if __name__ == "__main__":
    app = KanbanCSVApp()
    app.mainloop()
