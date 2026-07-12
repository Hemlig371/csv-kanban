import sys
import csv
import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import gc

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_MAIN = "#1e1e1e"
BG_PANEL = "#252526"
BG_CARD = "#4d4d4d"
FG_TEXT = "#e1e1e1"
BORDER_COLOR = "#3f3f46"
PAGE_SIZE = 25

FONT_TITLE = ("Arial", 18, "bold")
FONT_HEADER = ("Arial", 16, "bold")
FONT_TEXT_BOLD = ("Arial", 15, "bold")
FONT_MAIN = ("Arial", 16)
FONT_CARD = ("Arial", 15)
FONT_MUTED_ITALIC = ("Arial", 16, "italic")


class AutoHideScrollbar(ctk.CTkScrollbar):
    def set(self, low, high):
        if float(low) <= 0.0 and float(high) >= 1.0:
            self.pack_forget()
        else:
            if self.cget("orientation") == "vertical":
                self.pack(side="right", fill="y")
            else:
                self.pack(side="bottom", fill="x")
        super().set(low, high)


class KanbanCSVApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CSV Kanban")
        self.configure(fg_color=BG_MAIN)
        self._resize_timers = {}

        try:
            if os.path.exists("icon.ico"):
                self.iconbitmap("icon.ico")
            elif os.path.exists("icon.png"):
                img = tk.PhotoImage(file="icon.png")
                self.iconphoto(True, img)
        except: pass

        self.tabs_data = {}
        self.active_tab = None

        self.init_main_ui()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width, height = 1460, 980
        self.geometry(f"{width}x{height}+{(screen_w-width)//2}+{(screen_h-height)//2}")
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(100, self.restore_session)
        
        self.bind_all("<Control-Key>", self.handle_global_shortcuts)
        self.after(200, self.check_command_line_args)

    def center_toplevel(self, top, width, height):
        top.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (width // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (height // 2)
        top.geometry(f"{width}x{height}+{x}+{y}")

    def on_closing(self):
        session_data = []
        for title, d in self.tabs_data.items():
            if os.path.exists(d["file_path"]):
                session_data.append({
                    "file_path": d["file_path"],
                    "enc": d["enc"],
                    "sep": d["sep"],
                    "kanban_column": d["kanban_column"],
                    "text_column": d["text_column"]
                })
        try:
            with open("session.json", "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=4)
        except:
            pass
        self.destroy()

    def restore_session(self):
        if not os.path.exists("session.json"): return
        
        try:
            with open("session.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)
        except Exception as e:
            return
            
        if not isinstance(session_data, list): return

        for item in session_data:
            fp = item.get("file_path")
            if not fp or not os.path.exists(fp):
                continue
                
            try:
                enc = item.get("enc", "utf-8")
                sep = item.get("sep", ",")
                
                data = []
                with open(fp, "r", encoding=enc) as f:
                    reader = csv.DictReader(f, delimiter=sep)
                    headers = reader.fieldnames
                    for row in reader:
                        data.append(row)
                
                self.finalize_open(
                    fp, headers, data, sep, enc, 
                    kanban_col=item.get("kanban_column"), 
                    text_col=item.get("text_column")
                )
            except Exception as file_error:
                messagebox.showerror(
                    "Ошибка загрузки файла", 
                    f"Не удалось восстановить файл:\n{os.path.basename(fp)}\n\nОшибка: {file_error}"
                )
        if self.tabs_data:
            self.after(200, self._force_render_tabs)
                
    def _force_render_tabs(self):
            tabs = list(self.tabs_data.keys())
            if not tabs: 
                return
                
            self.tab_control.set(tabs[0])
            self.update_idletasks()
            
            active_data = self.tabs_data[tabs[0]]
            root_canvas = active_data.get("scroll_root")
            if root_canvas:
                root_canvas.configure(scrollregion=root_canvas.bbox("all"))
                
            self.on_tab_changed()

    def init_main_ui(self):
        self.top_bar = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=65)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)

        self.btn_open = ctk.CTkButton(self.top_bar, text="Открыть", command=self.open_file, font=FONT_MAIN, fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1, width=120, height=45)
        self.btn_open.pack(side="left", padx=10)

        self.btn_save = ctk.CTkButton(self.top_bar, text="Сохранить", command=self.save_file, font=FONT_MAIN, fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1, width=120, height=45)
        self.btn_save.pack(side="left", padx=5)

        self.btn_save_as = ctk.CTkButton(self.top_bar, text="Сохранить как...", command=self.save_file_as, font=FONT_MAIN, fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1, width=170, height=45)
        self.btn_save_as.pack(side="left", padx=5)

        self.btn_change_col = ctk.CTkButton(self.top_bar, text="Колонки", command=self.setup_kanban_columns_dialog, font=FONT_MAIN, fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1, width=120, height=45)
        self.btn_add_card = ctk.CTkButton(self.top_bar, text="+ Запись", command=self.add_new_card, font=FONT_TEXT_BOLD, fg_color="#007acc", text_color="white", width=120, height=45)

        self.lbl_status = ctk.CTkLabel(self.top_bar, text="Файлы не загружены.", font=FONT_MUTED_ITALIC, text_color=FG_TEXT)
        self.lbl_status.pack(side="left", padx=20)

        self.lbl_global_notify = ctk.CTkLabel(self.top_bar, text="", font=FONT_TEXT_BOLD, text_color="#10b981")
        self.lbl_global_notify.pack(side="left", padx=10)

        self.btn_close_tab = ctk.CTkButton(self.top_bar, text="Закрыть ✕", command=self.close_current_tab, font=FONT_MAIN, fg_color="#a83232", hover_color="#822525", width=120, height=40)

        self.work_area = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.work_area.pack(fill="both", expand=True, padx=5, pady=5)

        self.right_editor_frame = ctk.CTkFrame(self.work_area, fg_color=BG_PANEL, width=440, border_color=BORDER_COLOR, border_width=1, corner_radius=8)
        self.right_editor_frame.pack(side="right", fill="y", padx=5, pady=5)
        self.right_editor_frame.pack_propagate(False)

        self.left_frame = ctk.CTkFrame(self.work_area, fg_color=BG_MAIN, corner_radius=0)
        self.left_frame.pack(side="left", fill="both", expand=True)

        self.tab_control = ctk.CTkTabview(self.left_frame, fg_color=BG_MAIN, command=self.on_tab_changed)
        self.tab_control._segmented_button.configure(font=FONT_MAIN)
        self.tab_control.pack(fill="both", expand=True)

        self.editor_widgets = {}
        self.current_editing_row = None
        self.show_editor_placeholder()

    def show_notification(self, text, color="#10b981"):
        self.lbl_global_notify.configure(text=text, text_color=color)
        self.after(3000, lambda: self.lbl_global_notify.configure(text=""))
        
    def update_status_bar(self):
        if not self.active_tab:
            self.lbl_status.configure(text="Файлы не загружены.", text_color=FG_TEXT)
            return
        d = self.tabs_data[self.active_tab]
        status_text = f"Строк: {len(d['data'])}"
        
        if d.get("is_unsaved", False):
            status_text += "  |  * НЕ СОХРАНЕНО"
            self.lbl_status.configure(text=status_text, text_color="#facc15")
        else:
            self.lbl_status.configure(text=status_text, text_color=FG_TEXT)

    def get_target_text_widget(self):
        w = self.focus_get()
        if not w: return None
        if isinstance(w, (tk.Entry, tk.Text)): return w
        if hasattr(w, "_entry"): return w._entry
        if hasattr(w, "_textbox"): return w._textbox
        if 'entry' in str(type(w)).lower() or 'textbox' in str(type(w)).lower(): return w
        return None

    def handle_global_shortcuts(self, event):
        key = event.keysym.lower()
        if key == 'o':
            self.open_file()
            return "break"
        elif key == 's':
            self.save_file()
            return "break"
        
        w = self.get_target_text_widget()
        if not w: return

        if key == 'v' or event.keycode == 86 or getattr(event, 'keysym_num', 0) == 244:
            self.global_paste(None)
            return "break"
        elif key == 'c' or event.keycode == 67 or getattr(event, 'keysym_num', 0) == 241:
            self.global_copy(None)
            return "break"
        elif key == 'x' or event.keycode == 88 or getattr(event, 'keysym_num', 0) == 231:
            self.global_cut(w)
            return "break"
        elif key == 'a' or event.keycode == 65 or getattr(event, 'keysym_num', 0) == 245:
            self.global_select_all(None)
            return "break"

    def global_cut(self, widget):
        self.global_copy(None)
        try:
            if isinstance(widget, tk.Text) or 'text' in str(type(widget)).lower():
                widget.delete("sel.first", "sel.last")
            else:
                widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except: pass

    def global_paste(self, widget):
        if not widget: return
        try:
            text = self.clipboard_get()
            if text:
                if isinstance(widget, tk.Text) or 'text' in str(type(widget)).lower():
                    widget.insert(tk.INSERT, text)
                else:
                    try: widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    except: pass
                    widget.insert(tk.INSERT, text)
        except: 
            pass

    def global_copy(self, widget):
        if not widget: return
        try:
            if isinstance(widget, tk.Text) or 'text' in str(type(widget)).lower():
                text = widget.get("sel.first", "sel.last")
            else:
                text = widget.selection_get()
            
            if text:
                self.clipboard_clear()
                self.clipboard_append(text)
        except: 
            pass

    def global_select_all(self, widget):
        if not widget: return
        if isinstance(widget, tk.Text) or 'text' in str(type(widget)).lower():
            widget.tag_add("sel", "1.0", "end")
            widget.mark_set(tk.INSERT, "1.0")
        elif hasattr(widget, "select_range"):
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)

    def show_context_menu(self, event, widget):
        widget.focus_set()
        
        if hasattr(self, "_active_menu"):
            self._active_menu.destroy()
            
        self._active_menu = tk.Menu(self, tearoff=0, bg=BG_PANEL, fg=FG_TEXT, selectcolor="#007acc")
        self._active_menu.add_command(label="Вырезать", command=lambda: self.global_cut(widget))
        self._active_menu.add_command(label="Копировать", command=lambda: self.global_copy(widget))
        self._active_menu.add_command(label="Вставить", command=lambda: self.global_paste(widget))
        self._active_menu.add_separator()
        self._active_menu.add_command(label="Выделить всё", command=lambda: self.global_select_all(widget))
        self._active_menu.tk_popup(event.x_root, event.y_root)

    def check_command_line_args(self):
        if len(sys.argv) > 1:
            fp = sys.argv[1]
            if os.path.exists(fp):
                enc = "utf-8"
                sep = ","
                
                try:
                    data = []
                    with open(fp, "r", encoding=enc) as f:
                        reader = csv.DictReader(f, delimiter=sep)
                        headers = reader.fieldnames
                        for row in reader:
                            data.append(row)
                    
                    self.finalize_open(fp, headers, data, sep, enc)
                except Exception as e:
                    messagebox.showerror("Ошибка при автозагрузке", str(e))
                    self.show_import_dialog(fp)
                
    def open_file(self):
        fp = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not fp: return
        self.show_import_dialog(fp)

    def show_import_dialog(self, fp):
        win = ctk.CTkToplevel(self)
        win.title("Настройки импорта")
        self.center_toplevel(win, 620, 480)
        win.grab_set()

        enc_var = tk.StringVar(win, value="utf-8")
        sep_var = tk.StringVar(win, value=",")

        top_frame = ctk.CTkFrame(win, fg_color="transparent")
        top_frame.pack(pady=(20, 10), fill="x", padx=20)

        ctk.CTkLabel(top_frame, text="Кодировка:", font=FONT_MAIN).pack(side="left", padx=(0, 5))
        encodings_list = ["utf-8", "windows-1251", "cp866", "utf-8-sig", "utf-16", "latin-1"]
        enc_combo = ctk.CTkComboBox(top_frame, variable=enc_var, values=encodings_list, font=FONT_MAIN, width=150)
        enc_combo.pack(side="left", padx=5)

        ctk.CTkLabel(top_frame, text="Разделитель:", font=FONT_MAIN).pack(side="left", padx=(20, 5))
        separators_list = [";", ",", "|", "\\t"]
        sep_combo = ctk.CTkComboBox(top_frame, variable=sep_var, values=separators_list, font=FONT_MAIN, width=80)
        sep_combo.pack(side="left", padx=5)

        ctk.CTkLabel(win, text="Предпросмотр данных (первые 5 строк):", font=FONT_MAIN).pack(anchor="w", padx=20, pady=(15, 5))
        
        preview_text = ctk.CTkTextbox(win, height=220, font=("Courier", 14), wrap="none")
        preview_text.pack(fill="both", expand=True, padx=20, pady=5)

        def update_preview(*args):
            enc = enc_var.get()
            raw_sep = sep_var.get()
            actual_sep = "\t" if raw_sep == "\\t" else raw_sep
            
            preview_text.configure(state="normal")
            preview_text.delete("1.0", "end")
            
            if len(actual_sep) != 1:
                preview_text.insert("1.0", "Разделитель должен состоять строго из 1 символа.")
                preview_text.configure(state="disabled")
                return

            try:
                with open(fp, "r", encoding=enc) as f:
                    reader = csv.reader(f, delimiter=actual_sep)
                    lines = []
                    for i, row in enumerate(reader):
                        if i >= 5: break
                        lines.append(" │ ".join(row))
                    preview_text.insert("1.0", "\n".join(lines))
            except Exception as e:
                preview_text.insert("1.0", f"Ошибка чтения файла:\n{e}")
            
            preview_text.configure(state="disabled")

        enc_var.trace_add("write", update_preview)
        sep_var.trace_add("write", update_preview)
        
        update_preview()

        def run_import(event=None):
            enc = enc_var.get()
            raw_sep = sep_var.get()
            actual_sep = "\t" if raw_sep == "\\t" else raw_sep
            
            if len(actual_sep) != 1:
                messagebox.showerror("Ошибка", "Разделитель должен быть одним символом.")
                return

            try:
                data = []
                with open(fp, "r", encoding=enc) as f:
                    reader = csv.DictReader(f, delimiter=actual_sep)
                    headers = reader.fieldnames
                    for i, row in enumerate(reader):
                        if i >= 10000:
                            messagebox.showwarning("Ограничение загрузки", "Файл содержит более 10 000 строк.")
                            break
                        data.append(row)
                
                self.finalize_open(fp, headers, data, actual_sep, enc)
                win.destroy()
            except Exception as e: 
                messagebox.showerror("Ошибка", str(e))

        ctk.CTkButton(win, text="Импортировать", command=run_import, font=FONT_TEXT_BOLD, width=200, height=40).pack(pady=20)
        win.bind('<Return>', run_import)

    def finalize_open(self, fp, headers, data, sep, enc, kanban_col=None, text_col=None):
        title = os.path.basename(fp)
        while title in self.tabs_data: title += "_"
        
        class Dialect(csv.excel): delimiter = sep
        
        self.tab_control.add(title)
        root_tab = self.tab_control.tab(title)
        canvas = tk.Canvas(root_tab, bg=BG_MAIN, highlightthickness=0)
        h_scroll = AutoHideScrollbar(root_tab, orientation="horizontal", command=canvas.xview)
        canvas.configure(xscrollcommand=h_scroll.set)
        
        h_scroll.pack(side="bottom", fill="x")
        canvas.pack(side="top", fill="both", expand=True)
        
        cnt = ctk.CTkFrame(canvas, fg_color=BG_MAIN)
        canvas.create_window((0, 0), window=cnt, anchor="nw")
        cnt.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        self.tabs_data[title] = {
            "file_path": fp, "headers": headers, "data": data, "csv_dialect": Dialect,
            "sep": sep, "enc": enc, "kanban_column": kanban_col, "text_column": text_col, 
            "column_pages": {}, "column_data_map": {}, "container": cnt, "scroll_root": canvas,
            "is_unsaved": False
        }
        self.tab_control.set(title)
        self.on_tab_changed()
        
        if kanban_col:
            self.build_board()
        else:
            self.setup_kanban_columns_dialog()

    def on_tab_changed(self):
        self.active_tab = self.tab_control.get()
        if not self.active_tab:
            for b in [self.btn_change_col, self.btn_add_card, self.btn_close_tab]: b.pack_forget()
            self.show_editor_placeholder()
            self.update_status_bar()
            return
            
        self.update_status_bar()
        self.btn_change_col.pack(side="right", padx=10)
        self.btn_add_card.pack(side="right", padx=5)
        self.btn_close_tab.pack(side="right", padx=10)
        self.show_editor_placeholder()

    def close_current_tab(self, force=False):
        t = self.active_tab
        if not t: return
        
        d = self.tabs_data[t]
        if not force:
            warn_text = f"Закрыть {t}?"
            if d.get("is_unsaved"):
                warn_text = f"В файле {t} есть НЕСОХРАНЕННЫЕ изменения!\nВсе равно закрыть?"
                
            if not messagebox.askyesno("Подтверждение", warn_text):
                return

        self.tab_control.delete(t)
        d["container"].destroy()
        d["scroll_root"].destroy()
        del self.tabs_data[t]
        self.on_tab_changed()

    def setup_kanban_columns_dialog(self):
        d = self.tabs_data[self.active_tab]
        win = ctk.CTkToplevel(self)
        win.title("Настройки")
        self.center_toplevel(win, 500, 350)
        win.grab_set()
        
        ctk.CTkLabel(win, text="Группировать по:", font=FONT_HEADER).pack(pady=(20,5))
        c1 = ctk.CTkComboBox(win, values=d["headers"], width=300)
        c1.pack(pady=5); c1.set(d["kanban_column"] or d["headers"][0])
        
        ctk.CTkLabel(win, text="Многострочное поле:", font=FONT_HEADER).pack(pady=(15,5))
        c2 = ctk.CTkComboBox(win, values=["[Нет]"] + d["headers"], width=300)
        c2.pack(pady=5); c2.set(d["text_column"] or "[Нет]")

        found_text_field = next((h for h in d["headers"] if h.lower() in ["текст", "text"]), None)
        if found_text_field:
            c2.set(found_text_field)
        else:
            c2.set(d["text_column"] or "[Нет]")
        
        def apply(event=None):
            selected_col = c1.get()
            unique_vals = set(str(r.get(selected_col, "")).strip() for r in d["data"])
            if len(unique_vals) > 20:
                messagebox.showwarning("Ошибка", f"Слишком много групп ({len(unique_vals)})")
                return
            
            d["kanban_column"] = selected_col
            d["text_column"] = None if c2.get() == "[Нет]" else c2.get()
            win.destroy()
            self.build_board()
            
        ctk.CTkButton(win, text="OK", command=apply, font=FONT_TEXT_BOLD).pack(pady=30)
        win.bind('<Return>', apply)

    def _create_scroll_cmd(self, canvas):
        def scroll(e):
            low, high = canvas.yview()
            if low <= 0.0 and high >= 1.0:
                return
            eps = 0.01 
            
            if low <= 0.0 and e.delta > 0:
                return
            if high >= (1.0 - eps) and e.delta < 0:
                return
                
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            
        return scroll

    def build_board(self):
        d = self.tabs_data[self.active_tab]
        
        d["column_data_map"].clear()
        for r in d["data"]:
            v = str(r.get(d["kanban_column"], "")).strip() or "[Пусто]"
            d["column_data_map"].setdefault(v, []).append(r)
        
        new_cnt = ctk.CTkFrame(d["scroll_root"], fg_color=BG_MAIN)
        d["pagination_refs"] = {}
        
        keys = sorted(d["column_data_map"].keys())
        for i, v in enumerate(keys):
            new_cnt.grid_columnconfigure(i, weight=0, minsize=330)
            f = ctk.CTkFrame(new_cnt, fg_color=BG_PANEL, border_color=BORDER_COLOR, border_width=1, width=320, height=830)
            f.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            f.pack_propagate(False)
            
            ctk.CTkLabel(f, text=f"{v.upper()} ({len(d['column_data_map'][v])})", font=FONT_HEADER, fg_color="transparent").pack(pady=10)
            
            pag_frame = ctk.CTkFrame(f, fg_color="transparent")
            pag_frame.pack(side="bottom", fill="x", pady=5, padx=5)
            
            btn_prev = ctk.CTkButton(pag_frame, text="◄", width=35, command=lambda col=v: self.change_page(col, -1))
            btn_prev.pack(side="left")
            
            lbl_page = ctk.CTkLabel(pag_frame, text="", font=FONT_CARD)
            lbl_page.pack(side="left", expand=True)
            
            btn_next = ctk.CTkButton(pag_frame, text="►", width=35, command=lambda col=v: self.change_page(col, 1))
            btn_next.pack(side="right")
            
            col_canvas = tk.Canvas(f, bg=BG_PANEL, highlightthickness=0)
            v_scroll = AutoHideScrollbar(f, orientation="vertical", command=col_canvas.yview)
            col_canvas.configure(yscrollcommand=v_scroll.set)
            
            v_scroll.pack(side="right", fill="y")
            col_canvas.pack(side="left", fill="both", expand=True)
            
            sf = ctk.CTkFrame(col_canvas, fg_color=BG_PANEL, corner_radius=0)
            col_canvas.create_window((0,0), window=sf, anchor="nw")
            
            def throttled_resize(e, cv=col_canvas, key=v):
                if key in self._resize_timers:
                    self.after_cancel(self._resize_timers[key])
                self._resize_timers[key] = self.after(100, lambda: cv.configure(scrollregion=cv.bbox("all")))
            
            sf.bind("<Configure>", throttled_resize)
            f.bind("<Configure>", lambda e, cv=col_canvas: cv.configure(scrollregion=cv.bbox("all")))
            
            current_page = d["column_pages"].get(v, 0)
            max_page = max(0, (len(d["column_data_map"][v]) - 1) // PAGE_SIZE)
            if current_page > max_page: 
                current_page = max_page
            d["column_pages"][v] = current_page
            
            d["pagination_refs"][v] = {
                "sf": sf, 
                "lbl": lbl_page, 
                "btn_prev": btn_prev, 
                "btn_next": btn_next,
                "canvas": col_canvas
            }
            
            scroll_cmd = self._create_scroll_cmd(col_canvas)
            col_canvas.bind("<Enter>", lambda e: [col_canvas.focus_set(), col_canvas.bind("<MouseWheel>", scroll_cmd)])
            col_canvas.bind("<Leave>", lambda e: col_canvas.unbind("<MouseWheel>"))

        for v in keys:
            self.render_page(v)
            
        new_cnt.update_idletasks()
        
        old_cnt = d["container"]
        d["container"] = new_cnt
        d["scroll_root"].create_window((0, 0), window=new_cnt, anchor="nw")
        
        if old_cnt:
            old_cnt.destroy()
        
        new_cnt.bind("<Configure>", lambda e: d["scroll_root"].configure(scrollregion=d["scroll_root"].bbox("all")))

    def render_page(self, v):
        d = self.tabs_data[self.active_tab]
        page_idx = d["column_pages"][v]
        refs = d["pagination_refs"][v]
        
        old_sf = refs["sf"]
        items = d["column_data_map"].get(v, [])
        
        total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
        
        refs["lbl"].configure(text=f"Стр. {page_idx + 1} из {total_pages}")
        refs["btn_prev"].configure(state="normal" if page_idx > 0 else "disabled")
        refs["btn_next"].configure(state="normal" if page_idx < total_pages - 1 else "disabled")
        
        new_sf = ctk.CTkFrame(refs["canvas"], fg_color=BG_PANEL, corner_radius=0, width=310)
        
        start = page_idx * PAGE_SIZE
        end = start + PAGE_SIZE
        rows = items[start:end]
        
        for r in rows:
            card = ctk.CTkFrame(new_sf, fg_color=BG_CARD, border_color=BORDER_COLOR, border_width=1, cursor="hand2", width=310)
            card.pack(padx=8, pady=5)
            
            txt = "\n".join([f"• {h}: {str(r.get(h,''))[:40]}" for h in d["headers"][:4]])
            lbl = ctk.CTkLabel(card, text=txt, font=FONT_CARD, justify="left", anchor="w", wraplength=320)
            lbl.pack(fill="both", padx=10, pady=10)
            
            for w in [card, lbl]: w.bind("<Double-1>", lambda e, row_ref=r: self.load_editor(row_ref))
            
        def throttled_resize(e, cv=refs["canvas"], key=v):
            if key in self._resize_timers:
                self.after_cancel(self._resize_timers[key])
            self._resize_timers[key] = self.after(100, lambda: cv.configure(scrollregion=cv.bbox("all")))
            
        new_sf.bind("<Configure>", throttled_resize)
        scroll_cmd = self._create_scroll_cmd(refs["canvas"])
        new_sf.bind("<Enter>", lambda e, cv=refs["canvas"], cmd=scroll_cmd: [cv.focus_set(), cv.bind("<MouseWheel>", cmd)])
        new_sf.bind("<Leave>", lambda e, cv=refs["canvas"]: cv.unbind("<MouseWheel>"))

        new_sf.update_idletasks()
        
        refs["canvas"].create_window((0,0), window=new_sf, anchor="nw")
        refs["sf"] = new_sf
        
        if old_sf and old_sf.winfo_exists():
            old_sf.destroy()
            
        refs["canvas"].yview_moveto(0)

    def change_page(self, v, direction):
        d = self.tabs_data[self.active_tab]
        d["column_pages"][v] += direction
        self.render_page(v)

    def show_editor_placeholder(self):
        for w in self.right_editor_frame.winfo_children(): w.destroy()
        self.current_editing_row = None
        ctk.CTkLabel(self.right_editor_frame, text="").pack(fill="both", expand=True)

    def load_editor(self, row, is_new=False):
        for w in self.right_editor_frame.winfo_children(): w.destroy()
        self.current_editing_row = row
        d = self.tabs_data[self.active_tab]
        
        ctk.CTkLabel(self.right_editor_frame, text="Запись", font=FONT_TITLE).pack(pady=10)
        
        bf = ctk.CTkFrame(self.right_editor_frame, fg_color=BG_PANEL)
        bf.pack(fill="x", side="bottom", pady=15, padx=15)
        
        ctk.CTkButton(bf, text="Отмена", command=self.show_editor_placeholder, width=130, height=40, font=FONT_MAIN).pack(side="right", padx=5)
        ctk.CTkButton(bf, text="Сохранить", command=lambda: self.save_edit(is_new), fg_color="#007acc", width=130, height=40, font=FONT_TEXT_BOLD).pack(side="right", padx=5)

        if not is_new:
            ctk.CTkButton(bf, text="Удалить", command=self.delete_current_record, fg_color="#a83232", hover_color="#822525", width=100, height=40, font=FONT_MAIN).pack(side="left", padx=5)

        editor_canvas = tk.Canvas(self.right_editor_frame, bg=BG_PANEL, highlightthickness=0)
        ed_scroll = AutoHideScrollbar(self.right_editor_frame, orientation="vertical", command=editor_canvas.yview)
        editor_canvas.configure(yscrollcommand=ed_scroll.set)
        
        ed_scroll.pack(side="right", fill="y")
        editor_canvas.pack(side="left", fill="both", expand=True)
        
        sf = ctk.CTkFrame(editor_canvas, fg_color=BG_PANEL)
        canvas_frame_id = editor_canvas.create_window((0,0), window=sf, anchor="nw")
        
        editor_canvas.bind('<Configure>', lambda e, cv=editor_canvas, fid=canvas_frame_id: cv.itemconfigure(fid, width=e.width))
        sf.bind("<Configure>", lambda e, cv=editor_canvas: cv.configure(scrollregion=cv.bbox("all")))
        
        scroll_cmd = self._create_scroll_cmd(editor_canvas)
        editor_canvas.bind("<Enter>", lambda e, cv=editor_canvas, cmd=scroll_cmd: [cv.focus_set(), cv.bind("<MouseWheel>", cmd)])
        editor_canvas.bind("<Leave>", lambda e, cv=editor_canvas: cv.unbind("<MouseWheel>"))
        sf.bind("<Enter>", lambda e, cv=editor_canvas, cmd=scroll_cmd: [cv.focus_set(), cv.bind("<MouseWheel>", cmd)])
        self.editor_widgets = {}
        st_list = sorted(list(set(str(r.get(d["kanban_column"], "")).strip() for r in d["data"] if r.get(d["kanban_column"], ""))))

        for h in d["headers"]:
            f = ctk.CTkFrame(sf, fg_color=BG_PANEL)
            f.pack(fill="x", pady=5, padx=10)
            ctk.CTkLabel(f, text=h, font=FONT_HEADER).pack(anchor="w")
            
            if h == d["kanban_column"]:
                w = ctk.CTkComboBox(f, values=[""] + st_list, font=FONT_MAIN, height=40)
                w.set(" " if is_new else str(row.get(h, "")))
                target_w = w._entry
            elif h == d["text_column"]:
                w = ctk.CTkTextbox(f, font=FONT_MAIN, height=180, border_width=1)
                w.insert("1.0", str(row.get(h, "")))
                target_w = w._textbox
            else:
                w = ctk.CTkEntry(f, font=FONT_MAIN, height=40)
                w.insert(0, str(row.get(h, "")))
                target_w = w._entry
                
            w.pack(fill="x", pady=2, padx=(0, 5))
            self.editor_widgets[h] = w
            target_w.bind("<Button-3>", lambda event, tw=target_w: self.show_context_menu(event, tw))

    def save_edit(self, is_new):
        d = self.tabs_data[self.active_tab]
        res = {}
        for h, w in self.editor_widgets.items():
            res[h] = w.get("1.0", "end-1c").strip() if isinstance(w, ctk.CTkTextbox) else w.get().strip()
        
        if not res.get(d["kanban_column"]): return
        self.current_editing_row.update(res)
        if is_new: d["data"].append(self.current_editing_row)

        d["is_unsaved"] = True
        self.update_status_bar()
        self.build_board()
        self.show_editor_placeholder()
        self.show_notification("Изменения применены", "#10b981")

    def delete_current_record(self):
        d = self.tabs_data.get(self.active_tab)
        if not d or not self.current_editing_row: return
        
        if messagebox.askyesno("Удаление", "Удалить выбранную запись безвозвратно?"):
            for i, row in enumerate(d["data"]):
                if row is self.current_editing_row:
                    del d["data"][i]
                    d["is_unsaved"] = True
                    self.update_status_bar()
                    self.build_board()
                    self.show_editor_placeholder()
                    self.show_notification("Запись удалена", "#a83232")
                    return
            
            messagebox.showerror("Ошибка", "Запись не найдена.")

    def add_new_card(self):
        if self.active_tab: self.load_editor({h: "" for h in self.tabs_data[self.active_tab]["headers"]}, True)

    def save_file_as(self):
        if not self.active_tab: return
        d = self.tabs_data[self.active_tab]
        fp = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            filetypes=[("CSV Files", "*.csv")],
            initialfile=os.path.basename(d["file_path"]),
            title="Сохранить как..."
        )
        if not fp: return
        
        enc, sep = d["enc"], d["sep"]
        k_col, t_col = d["kanban_column"], d["text_column"]
        headers = d["headers"]
        data_copy = [dict(row) for row in d["data"]]
        
        try:
            with open(fp, "w", encoding=enc, newline="") as f:
                w = csv.DictWriter(f, fieldnames=headers, delimiter=sep)
                w.writeheader()
                w.writerows(data_copy)
            self.show_notification("Новый файл сохранен!", "#10b981")
        except Exception as e: 
            messagebox.showerror("Ошибка", str(e))
            return
            
        self.close_current_tab(force=True)
        self.finalize_open(fp, headers, data_copy, sep, enc, kanban_col=k_col, text_col=t_col)

    def save_file(self):
        if not self.active_tab: return
        d = self.tabs_data[self.active_tab]
        try:
            with open(d["file_path"], "w", encoding=d["enc"], newline="") as f:
                w = csv.DictWriter(f, fieldnames=d["headers"], delimiter=d["sep"])
                w.writeheader()
                w.writerows(d["data"])
            
            d["is_unsaved"] = False
            self.update_status_bar()
            self.show_notification("Файл успешно сохранен!", "#10b981")
        except PermissionError:
            messagebox.showerror("Ошибка доступа", f"Не удалось сохранить файл.\nВозможно, он открыт в другой программе.")
        except Exception as e: 
            messagebox.showerror("Ошибка", str(e))


if __name__ == "__main__":
    KanbanCSVApp().mainloop()
