import csv
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import gc

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG_MAIN = "#1e1e1e"
BG_PANEL = "#252526"
BG_CARD = "#2d2d30"
FG_TEXT = "#e1e1e1"
FG_MUTED = "#858585"
BORDER_COLOR = "#3f3f46"

PAGE_SIZE = 25

FONT_TITLE = ("Arial", 18, "bold")
FONT_HEADER = ("Arial", 16, "bold")
FONT_TEXT_BOLD = ("Arial", 15, "bold")
FONT_MAIN = ("Arial", 16)
FONT_CARD = ("Arial", 15)
FONT_MUTED_ITALIC = ("Arial", 16, "italic")


class KanbanCSVApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CSV Kanban")
        self.configure(fg_color=BG_MAIN)

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
        width, height = 1850, 1000
        self.geometry(f"{width}x{height}+{(screen_w-width)//2}+{(screen_h-height)//2}")
        
        self.bind_all("<Control-v>", self.global_paste)
        self.bind_all("<Control-c>", self.global_copy)
        self.bind_all("<Control-a>", self.global_select_all)

    def init_main_ui(self):
        self.top_bar = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=65)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)

        self.btn_open = ctk.CTkButton(self.top_bar, text="Открыть CSV (Ctrl+O)", command=self.open_file, font=FONT_MAIN, fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1, width=190, height=45)
        self.btn_open.pack(side="left", padx=10)

        self.btn_save = ctk.CTkButton(self.top_bar, text="Сохранить (Ctrl+S)", command=self.save_file, font=FONT_MAIN, fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1, width=190, height=45)
        self.btn_save.pack(side="left", padx=5)

        self.btn_change_col = ctk.CTkButton(self.top_bar, text="Настройка колонок", command=self.setup_kanban_columns_dialog, font=FONT_MAIN, fg_color=BG_CARD, text_color=FG_TEXT, border_color=BORDER_COLOR, border_width=1, width=190, height=45)
        
        self.btn_add_card = ctk.CTkButton(self.top_bar, text="+ Добавить запись", command=self.add_new_card, font=FONT_TEXT_BOLD, fg_color="#007acc", text_color="white", width=190, height=45)

        self.lbl_status = ctk.CTkLabel(self.top_bar, text="Файлы не загружены.", font=FONT_MUTED_ITALIC, text_color=FG_TEXT)
        self.lbl_status.pack(side="left", padx=20)

        self.btn_close_tab = ctk.CTkButton(self.top_bar, text="Закрыть ✕", command=self.close_current_tab, font=FONT_MAIN, fg_color="#a83232", hover_color="#822525", width=120, height=40)

        self.work_area = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.work_area.pack(fill="both", expand=True, padx=5, pady=5)

        self.right_editor_frame = ctk.CTkFrame(self.work_area, fg_color=BG_PANEL, width=520, border_color=BORDER_COLOR, border_width=1, corner_radius=8)
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

        self.bind_all("<Control-o>", lambda e: self.open_file())
        self.bind_all("<Control-s>", lambda e: self.save_file())

    def global_paste(self, event):
        w = self.focus_get()
        if isinstance(w, (tk.Entry, tk.Text)) or 'entry' in str(type(w)).lower() or 'textbox' in str(type(w)).lower():
            try:
                text = self.clipboard_get()
                if not text: return
                if hasattr(w, "insert"):
                    if 'textbox' in str(type(w)).lower() or isinstance(w, tk.Text):
                        w.insert(tk.INSERT, text)
                    else:
                        w.insert(tk.INSERT, text)
            except: pass
            return "break"

    def global_copy(self, event):
        w = self.focus_get()
        if isinstance(w, (tk.Entry, tk.Text)) or 'entry' in str(type(w)).lower() or 'textbox' in str(type(w)).lower():
            return

    def global_select_all(self, event):
        w = self.focus_get()
        if 'entry' in str(type(w)).lower():
            w.select_range(0, tk.END)
            w.icursor(tk.END)
            return "break"
        elif 'textbox' in str(type(w)).lower() or isinstance(w, tk.Text):
            w.tag_add("sel", "1.0", "end")
            return "break"

    def open_file(self):
        fp = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not fp: return
        try:
            with open(fp, "r", encoding="utf-8") as f:
                lines = [f.readline() for _ in range(5)]
            if not lines: return
            dlm = ';' if ';' in lines[0] else (',' if ',' in lines[0] else '\t')
            with open(fp, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=dlm)
                headers = reader.fieldnames
                data = list(reader)
            
            title = os.path.basename(fp)
            while title in self.tabs_data: title += "_"
            
            class Dialect(csv.excel): delimiter = dlm
            
            self.tab_control.add(title)
            scr = ctk.CTkScrollableFrame(self.tab_control.tab(title), fg_color=BG_MAIN, orientation="horizontal")
            scr.pack(fill="both", expand=True)
            cnt = ctk.CTkFrame(scr, fg_color=BG_MAIN)
            cnt.pack(fill="both", expand=True)
            
            self.tabs_data[title] = {
                "file_path": fp, "headers": headers, "data": data, "csv_dialect": Dialect,
                "kanban_column": None, "text_column": None, "column_pages": {}, 
                "column_data_map": {}, "container": cnt, "scroll_root": scr
            }
            self.tab_control.set(title)
            self.on_tab_changed()
            self.setup_kanban_columns_dialog()
        except Exception as e: messagebox.showerror("Error", str(e))

    def on_tab_changed(self):
        self.active_tab = self.tab_control.get()
        if not self.active_tab:
            for b in [self.btn_change_col, self.btn_add_card, self.btn_close_tab]: b.pack_forget()
            self.show_editor_placeholder()
            return
        d = self.tabs_data[self.active_tab]
        self.lbl_status.configure(text=f"Файл: {os.path.basename(d['file_path'])} | Строк: {len(d['data'])}")
        self.btn_change_col.pack(side="right", padx=10)
        self.btn_add_card.pack(side="right", padx=5)
        self.btn_close_tab.pack(side="right", padx=10)
        self.show_editor_placeholder()

    def close_current_tab(self):
        t = self.active_tab
        if not t: return
        if messagebox.askyesno("Confirm", f"Close {t}?"):
            self.tab_control.delete(t)
            d = self.tabs_data.pop(t)
            d["container"].destroy()
            d["scroll_root"].destroy()
            gc.collect()
            self.on_tab_changed()

    def setup_kanban_columns_dialog(self):
        d = self.tabs_data[self.active_tab]
        win = ctk.CTkToplevel(self)
        win.title("Config")
        win.geometry("500x350")
        win.grab_set()
        
        ctk.CTkLabel(win, text="Группировать по:", font=FONT_HEADER).pack(pady=(20,5))
        c1 = ctk.CTkComboBox(win, values=d["headers"], width=300)
        c1.pack(pady=5); c1.set(d["kanban_column"] or d["headers"][0])
        
        ctk.CTkLabel(win, text="Многострочное поле:", font=FONT_HEADER).pack(pady=(15,5))
        c2 = ctk.CTkComboBox(win, values=["[Нет]"] + d["headers"], width=300)
        c2.pack(pady=5); c2.set(d["text_column"] or "[Нет]")
        
        def apply():
            d["kanban_column"] = c1.get()
            d["text_column"] = None if c2.get() == "[Нет]" else c2.get()
            win.destroy(); self.build_board()
        ctk.CTkButton(win, text="OK", command=apply, font=FONT_TEXT_BOLD).pack(pady=30)

    def build_board(self):
        d = self.tabs_data[self.active_tab]; c = d["container"]
        for w in c.winfo_children(): w.destroy()
        
        d["column_data_map"] = {}
        for r in d["data"]:
            v = str(r.get(d["kanban_column"], "")).strip() or "[Пусто]"
            d["column_data_map"].setdefault(v, []).append(r)
        
        keys = sorted(d["column_data_map"].keys())
        for i, v in enumerate(keys):
            c.grid_columnconfigure(i, weight=0, minsize=380)
            f = ctk.CTkFrame(c, fg_color=BG_PANEL, border_color=BORDER_COLOR, border_width=1, width=370, height=800)
            f.grid(row=0, column=i, padx=5, pady=5, sticky="nsew")
            f.pack_propagate(False)
            
            ctk.CTkLabel(f, text=f"{v.upper()} ({len(d['column_data_map'][v])})", font=FONT_HEADER, fg_color="transparent").pack(pady=10)
            sf = ctk.CTkScrollableFrame(f, fg_color=BG_PANEL, corner_radius=0)
            sf.pack(fill="both", expand=True)
            
            d["column_pages"][v] = PAGE_SIZE
            
            if hasattr(sf, "_parent_canvas") and hasattr(sf, "_scrollbar"):
                sf._parent_canvas.bind("<Configure>", lambda e, f_target=sf: self.fix_scroll(f_target), add="+")
            
            def sl(v=v, sf=sf):
                if hasattr(sf, "_canvas") and sf._canvas.yview()[1] >= 0.9: self.load_more(v, sf)
            if hasattr(sf, "_canvas"): sf._canvas.bind("<MouseWheel>", lambda e, sl=sl: [sf._on_mousewheel(e), sl()], add="+")
            
            self.render_chunk(v, sf, 0, PAGE_SIZE)

    def render_chunk(self, v, sf, start, end):
        d = self.tabs_data[self.active_tab]
        rows = d["column_data_map"][v][start:end]
        for r in rows:
            card = ctk.CTkFrame(sf, fg_color=BG_CARD, border_color=BORDER_COLOR, border_width=1, cursor="hand2")
            card.pack(fill="x", padx=8, pady=5)
            
            txt = "\n".join([f"• {h}: {str(r.get(h,''))[:40]}" for h in d["headers"][:4]])
            lbl = ctk.CTkLabel(card, text=txt, font=FONT_CARD, justify="left", anchor="w", wraplength=320)
            lbl.pack(fill="both", padx=10, pady=10)
            
            for w in [card, lbl]: w.bind("<Double-1>", lambda e, r=r: self.load_editor(r))
        
        self.update_idletasks()
        self.fix_scroll(sf)

    def fix_scroll(self, sf):
        if hasattr(sf, "_parent_canvas") and hasattr(sf, "_scrollbar"):
            sf.update_idletasks()
            y = sf._parent_canvas.yview()
            if y[0] <= 0.0 and y[1] >= 1.0:
                sf._scrollbar.pack_forget()
            else:
                sf._scrollbar.pack(side="right", fill="y")

    def load_more(self, v, sf):
        d = self.tabs_data[self.active_tab]
        curr = d["column_pages"][v]
        if curr < len(d["column_data_map"][v]):
            d["column_pages"][v] += PAGE_SIZE
            self.render_chunk(v, sf, curr, curr + PAGE_SIZE)

    def show_editor_placeholder(self):
        for w in self.right_editor_frame.winfo_children(): w.destroy()
        self.current_editing_row = None
        ctk.CTkLabel(self.right_editor_frame, text="").pack(fill="both", expand=True)

    def load_editor(self, row, is_new=False):
        for w in self.right_editor_frame.winfo_children(): w.destroy()
        self.current_editing_row = row; d = self.tabs_data[self.active_tab]
        
        ctk.CTkLabel(self.right_editor_frame, text="Запись", font=FONT_TITLE).pack(pady=10)
        sf = ctk.CTkScrollableFrame(self.right_editor_frame, fg_color=BG_PANEL)
        sf.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.editor_widgets = {}
        st_list = sorted(list(set(str(r.get(d["kanban_column"], "")).strip() for r in d["data"] if r.get(d["kanban_column"], ""))))

        for h in d["headers"]:
            f = ctk.CTkFrame(sf, fg_color=BG_PANEL)
            f.pack(fill="x", pady=5)
            ctk.CTkLabel(f, text=h, font=FONT_HEADER).pack(anchor="w")
            
            if h == d["kanban_column"]:
                w = ctk.CTkComboBox(f, values=[""] + st_list, font=FONT_MAIN, height=40)
                w.set(" " if is_new else str(row.get(h, "")))
            elif h == d["text_column"]:
                w = ctk.CTkTextbox(f, font=FONT_MAIN, height=180, border_width=1)
                w.insert("1.0", str(row.get(h, "")))
            else:
                w = ctk.CTkEntry(f, font=FONT_MAIN, height=40)
                w.insert(0, str(row.get(h, "")))
            w.pack(fill="x", pady=2)
            self.editor_widgets[h] = w

        bf = ctk.CTkFrame(self.right_editor_frame, fg_color=BG_PANEL)
        bf.pack(fill="x", side="bottom", pady=20)
        ctk.CTkButton(bf, text="Отмена", command=self.show_editor_placeholder, width=120).pack(side="right", padx=10)
        ctk.CTkButton(bf, text="Сохранить", command=lambda: self.save_edit(is_new), fg_color="#007acc", width=120).pack(side="right")

    def save_edit(self, is_new):
        d = self.tabs_data[self.active_tab]; res = {}
        for h, w in self.editor_widgets.items():
            res[h] = w.get("1.0", "end-1c").strip() if isinstance(w, ctk.CTkTextbox) else w.get().strip()
        
        if not res.get(d["kanban_column"]): return
        self.current_editing_row.update(res)
        if is_new: d["data"].append(self.current_editing_row)
        
        self.build_board(); self.show_editor_placeholder()

    def add_new_card(self):
        if self.active_tab: self.load_editor({h: "" for h in self.tabs_data[self.active_tab]["headers"]}, True)

    def save_file(self):
        if not self.active_tab: return
        d = self.tabs_data[self.active_tab]
        try:
            with open(d["file_path"], "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=d["headers"], dialect=d["csv_dialect"])
                w.writeheader(); w.writerows(d["data"])
            messagebox.showinfo("OK", "Saved")
        except Exception as e: messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    KanbanCSVApp().mainloop()
