import os
import glob
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from miv_registry import MIVRegistry
import subprocess  # 🖥️ اجرای دستورات سیستمی مثل whoami
import pandas as pd
from console_text import ConsoleText
from helpwindow import HelpWindow
from editmiv import EditMIVWindow
from editmiv import DeleteMIVWindow
from miv_table_viewer import MIVTableViewer
from line_no_autocomplete import LineNoAutocompleteEntry
from MTO_Consumption_Window import MTOConsumptionWindow


class MIVApp(tk.Tk):
    FIXED_PROJECTS = ["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P12", "P13", "P15"]

    def __init__(self, registry):
        super().__init__()

        self.registry = registry
        self.title("مدیریت MIV")
        self.geometry("1000x700")
        self.configure(bg="white")
        self.project_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.create_menu()

        self.create_widgets()  # ساخت ویجت‌ها

        self.console_output("✅ نرم‌افزار با موفقیت بارگذاری شد.")

    def show_table_viewer(self, mode, project, line_no=None, last_n=None, filters=None):
        """
        نمایش پنجره MIVTableViewer با امکان فیلتر بر اساس ستون‌های مختلف
        """
        viewer = MIVTableViewer(
            self,
            self.registry,
            mode,
            project,
            line_no=line_no,
            last_n=last_n,
            filters=filters  # 🔸 پارامتر جدید
        )
        viewer.grab_set()

    def show_delete_window(self, line_no, project):
        DeleteMIVWindow(self, self.registry, line_no, project)

    def show_edit_window(self, line_no, project):
        EditMIVWindow(self, self.registry, line_no, project)

    def show_help_window(self):
        HelpWindow(self, console_widget=self.result_text)

    def console_output(self, message):
        self.result_text.insert(tk.END, message + "\n")
        self.result_text.see(tk.END)

    def create_widgets(self):
        # --- انتخاب پروژه ---
        frame_project = ttk.Frame(self)
        frame_project.grid(row=0, column=0, columnspan=2, pady=10, sticky="ew")

        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(frame_project, text="🔹 محدوده پروژه:").pack(side=tk.LEFT, padx=5)

        self.project_combo = ttk.Combobox(frame_project, textvariable=self.project_var, state="readonly")
        self.project_combo['values'] = self.FIXED_PROJECTS
        self.project_combo.pack(side=tk.LEFT, padx=5)

        ttk.Button(frame_project, text="بارگذاری پروژه", command=self.load_project).pack(side=tk.LEFT)

        # --- فرم ثبت رکورد ---
        frame_form = ttk.LabelFrame(self, text="ثبت MIV جدید")
        frame_form.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        labels = ["Line No", "MIV Tag", "Location", "Status", "Comment", "Registered For"]
        self.entries = {}

        for label in labels:
            row = ttk.Frame(frame_form)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label + ": ", width=15).pack(side=tk.LEFT)

            if label == "Line No":
                ent = LineNoAutocompleteEntry(row, self.registry)
            elif label == "Comment":
                ent = ttk.Entry(row, state="readonly")  # 👈 غیرقابل ویرایش
            else:
                ent = ttk.Entry(row)

            ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.entries[label] = ent

        # 🔒 Registered By
        row_rb = ttk.Frame(frame_form)
        row_rb.pack(fill=tk.X, pady=2)
        ttk.Label(row_rb, text="Registered By: ", width=15).pack(side=tk.LEFT)
        system_user = subprocess.check_output("whoami", shell=True).decode("utf-8").strip()
        lbl_rb = ttk.Label(row_rb, text=system_user, background="white", anchor="w", relief="sunken")
        lbl_rb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entries["Registered By"] = lbl_rb

        ttk.Button(frame_form, text="ثبت رکورد", command=self.register_record).pack(pady=10)

        # --- جستجو ---
        frame_search = ttk.LabelFrame(self, text="جستجو و نمایش")
        frame_search.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        row_search = ttk.Frame(frame_search)
        row_search.pack(fill=tk.X, pady=5)
        ttk.Label(row_search, text="Line No برای جستجو: ", width=20).pack(side=tk.LEFT)
        self.search_entry = LineNoAutocompleteEntry(row_search, self.registry)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row_search, text="جستجو", command=self.search_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(row_search, text="📋 نمایش MTO", command=self.show_mto_table).pack(side=tk.LEFT, padx=5)

        self.result_text = ConsoleText(frame_search, app=self, height=20, width=40)
        self.result_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        ttk.Button(self, text="خروجی Excel بگیر", command=self.export_excel).grid(row=2, column=0, columnspan=2,
                                                                                  pady=10)

        # self.complete_var = tk.BooleanVar()
        # complete_frame = ttk.Frame(frame_form)
        # complete_frame.pack(fill=tk.X, pady=2)
        # ttk.Checkbutton(complete_frame, text="آیا این خط MIV کامل شده است؟", variable=self.complete_var).pack(
        #     side=tk.LEFT)

        lbl_author = ttk.Label(self, text="H.IZADI", font=("Arial", 9), foreground="gray")
        lbl_author.grid(row=3, column=0, columnspan=2, pady=5, sticky="e")

    def show_mto_table(self):
        if not self.registry:
            self.console_output("⚠️ لطفاً ابتدا پروژه را بارگذاری کنید.")
            return

        line_no = self.search_entry.get().strip()
        if not line_no:
            self.console_output("⚠️ لطفاً Line No را وارد کنید.")
            return

        mto_items = self.registry.get_mto_items(line_no)
        if mto_items.empty:
            self.console_output("❌ هیچ آیتمی در MTO برای این Line No یافت نشد.")
            return

        # 🔸 ستون‌هایی که باید نمایش داده شوند (پارامتریک)
        columns_to_show = ["Itemcode", "Description", "UNIT", "LENGTH(M)", "QUANTITY"]

        # 🔳 ساخت پنجره جدید
        top = tk.Toplevel(self)
        top.title(f"MTO - Line {line_no}")
        top.geometry("700x400")

        # 📊 ساخت TreeView برای نمایش جدول
        tree = ttk.Treeview(top, columns=columns_to_show, show="headings")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        def export_pdf():
            from miv_table_viewer import MIVTableViewer

            # ✅ بررسی اینکه پروژه فعالی تنظیم شده باشد
            if not hasattr(self.registry, "current_project") or not self.registry.current_project:
                messagebox.showerror("خطا", "پروژه فعالی برای خروجی گرفتن مشخص نشده است.")
                return

            # ✅ ساخت ویوئر و ارسال ترکیب پروژه و شماره خط
            viewer = MIVTableViewer(
                master=self,
                registry=self.registry,
                mode="MTO",
                project=f"{self.registry.current_project} - خط: {line_no}"  # 👈 عنوان سفارشی
            )
            viewer.tree = tree  # ⬅️ ارسال جدول به ویوئر
            viewer.export_to_pdf()  # ⬅️ اجرای تابع خروجی PDF

        ttk.Button(top, text="📄 خروجی PDF", command=export_pdf).pack(pady=5)

        # 🪄 تنظیم عنوان ستون‌ها
        for col in columns_to_show:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor='center')

        # 📥 اضافه کردن ردیف‌ها
        for _, row in mto_items.iterrows():
            values = [row.get(col, "") for col in columns_to_show]
            tree.insert("", tk.END, values=values)

        # دکمه بستن
        ttk.Button(top, text="بستن", command=top.destroy).pack(pady=5)

    def load_project(self):
        project = self.project_var.get()
        if not project:
            self.console_output("⚠️ لطفاً یک پروژه انتخاب کنید.")
            return

        # مسیر فایل پروژه
        project_file = f"{project}.csv"

        if not os.path.exists(project_file):
            answer = messagebox.askyesno("پروژه موجود نیست",
                                         f"فایل پروژه {project_file} یافت نشد. آیا می‌خواهید بسازید؟")
            if answer:
                created, msg = self.registry.create_project(project)
                if created:
                    self.console_output(f"✅ پروژه {project} با موفقیت ساخته شد.")
                else:
                    self.console_output(f"❌ خطا در ساخت پروژه {project}: {msg}")
            else:
                self.console_output(f"⚠️ پروژه {project} بارگذاری نشد.")
                return

        # اگر اینجا هستیم یعنی پروژه وجود داره (یا ساخته شده)
        self.registry = MIVRegistry(project)
        # برو سراغ LineNoAutocompleteEntry و اگر وجود داشت، ریستش کن
        line_entry = self.entries.get("Line No")
        if isinstance(line_entry, LineNoAutocompleteEntry):
            line_entry.registry = self.registry

        self.console_output(f"✅ پروژه {project} بارگذاری شد.")

    def register_record(self):
        if not self.registry:
            self.console_output("⚠️ لطفاً ابتدا پروژه را بارگذاری کنید.")
            return

        # گرفتن داده‌ها از فرم (به جز comment و complete)
        data = {}
        for label in ["Line No", "MIV Tag", "Location", "Status", "Registered For"]:
            val = self.entries[label].get().strip()
            if not val:
                self.console_output(f"⚠️ لطفاً فیلد «{label}» را وارد کنید.")
                return
            data[label] = val

        data["Project"] = self.registry.project
        data["Registered By"] = self.entries["Registered By"].cget("text")
        data["Last Updated (Shamsi)"] = self.registry.get_shamsi_date()

        line_no = data["Line No"]

        # بررسی کامل بودن خط (بر اساس فایل مصرفی)
        if self.registry.is_line_miv_complete(line_no):
            self.console_output(f"❌ خط «{line_no}» کامل شده و امکان ثبت MIV جدید وجود ندارد.")
            return

        # بررسی تکراری بودن MIV Tag
        if self.registry.is_duplicate_miv(data["MIV Tag"]):
            self.console_output(f"❌ MIV Tag «{data['MIV Tag']}» قبلاً ثبت شده است.")
            return

        # پیشنهاد اصلاح Line No
        # suggested = self.registry.suggest_line_no(line_no)
        # if suggested and suggested != line_no:
        #     answer = messagebox.askyesno("تأیید Line No", f"آیا منظورت این بود؟ → «{suggested}»\nادامه دهیم؟")
        #     if not answer:
        #         self.console_output("⚠️ ثبت رکورد لغو شد.")
        #         return
        #     data["Line No"] = suggested
        # elif suggested is None:
        #     self.console_output(f"❌ هیچ Line No مشابهی با «{line_no}» در MTO پروژه یافت نشد.")
        #     return

        # باز کردن پنجره انتخاب آیتم‌های مصرفی از MTO
        from MTO_Consumption_Window import MTOConsumptionWindow

        def after_consumption_selected(comment_summary):
            # وقتی پنجره انتخاب بسته شد و خلاصه آماده شد:
            data["Comment"] = comment_summary
            data["Complete"] = "True" if self.registry.is_line_miv_complete(data["Line No"]) else "False"

            # ترتیب ستون‌ها مطابق فایل CSV
            row = [
                data["Project"],
                data["Line No"],
                data["MIV Tag"],
                data["Location"],
                data["Status"],
                data["Comment"],
                data["Registered For"],
                data["Registered By"],
                data["Last Updated (Shamsi)"],
                data["Complete"]
            ]
            self.registry.save_record(row)
            self.console_output("✅ رکورد با موفقیت ثبت شد.")

            # پاک‌سازی فرم‌ها
            for key, ent in self.entries.items():
                if isinstance(ent, tk.Entry):
                    ent.config(state="normal")  # در صورت readonly بودن
                    ent.delete(0, tk.END)
            self.entries["Comment"].config(state="readonly")

        # ایجاد و نمایش پنجره MTO Consumption
        MTOConsumptionWindow(self, self.registry, data["Line No"], data["Project"], after_consumption_selected)

    def search_record(self):
        if not self.registry:
            self.console_output("⚠️ لطفاً ابتدا پروژه را بارگذاری کنید.")
            return

        input_line_no = self.search_entry.get().strip()
        if not input_line_no:
            self.console_output("⚠️ لطفاً مقدار Line No را وارد کنید.")
            return

        # 📍 گرفتن چند پیشنهاد
        # suggestions = self.registry.get_line_no_suggestions(input_line_no, top_n=5)
        #
        # if not suggestions:
        #     self.console_output(f"❌ هیچ Line No مشابهی با «{input_line_no}» در MTO پروژه یافت نشد.")
        #     return

        # if self.registry.normalize_line_no(input_line_no) not in [self.registry.normalize_line_no(s) for s in
        #                                                           suggestions]:
        #     selected = self.ask_user_to_choose_suggestion(suggestions)
        #     if not selected:
        #         self.console_output("⚠️ جستجو لغو شد.")
        #         return
        #     input_line_no = selected

        # ✅ ادامه جستجو
        miv_records, mto_items, complete = self.registry.search_record(input_line_no)

        if miv_records is None or miv_records.empty:
            self.console_output(f"❌ هیچ رکورد MIV برای خط «{input_line_no}» یافت نشد.")
        else:
            self.show_search_results(miv_records, input_line_no)
            if complete:
                self.console_output(f"✅ خط «{input_line_no}» به‌طور کامل MIV شده است.")
            else:
                self.console_output(f"📌 خط «{input_line_no}» هنوز کامل نشده و امکان ثبت رکورد جدید وجود دارد.")

    def ask_user_to_choose_suggestion(self, suggestions):
        """
        یک پنجره کوچک برای انتخاب یکی از پیشنهادهای Line No نمایش می‌دهد.
        """

        def on_select():
            selected_index = listbox.curselection()
            if selected_index:
                selected_value.set(suggestions[selected_index[0]])
                win.destroy()
            else:
                selected_value.set("")

        win = tk.Toplevel()
        win.title("پیشنهاد Line No")
        win.geometry("300x200")
        win.grab_set()  # قفل کردن پنجره فعلی

        label = tk.Label(win, text="آیا منظورت یکی از این‌هاست؟", font=("Tahoma", 11))
        label.pack(pady=10)

        listbox = tk.Listbox(win, height=min(6, len(suggestions)))
        for s in suggestions:
            listbox.insert(tk.END, s)
        listbox.pack(padx=10, fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=10)

        select_btn = tk.Button(btn_frame, text="انتخاب", command=on_select)
        select_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(btn_frame, text="لغو", command=win.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)

        selected_value = tk.StringVar()
        win.wait_window()  # صبر کن تا پنجره بسته شود
        return selected_value.get() or None

    def show_search_results(self, records, line_no):
        top = tk.Toplevel(self)
        top.title(f"MIV Records - Line {line_no}")
        top.geometry("900x400")

        tree = ttk.Treeview(top, columns=self.registry.HEADERS, show="headings")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for col in self.registry.HEADERS:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor='center')

        for _, row in records.iterrows():
            values = [row.get(col, "") for col in self.registry.HEADERS]
            tree.insert("", tk.END, values=values)

        ttk.Button(top, text="بستن", command=top.destroy).pack(pady=5)

    def show_mto_items(self):
        line_no = self.search_entry.get().strip()
        if not line_no:
            self.console_output("⚠️ لطفاً ابتدا یک Line No وارد کنید.")
            return

        _, mto_items, _ = self.registry.search_record(line_no)

        if mto_items is None or mto_items.empty:
            self.console_output("⚠️ اطلاعات MTO برای این Line No موجود نیست.")
            return

        top = tk.Toplevel(self)
        top.title(f"MTO Items - Line {line_no}")
        top.geometry("800x400")

        # انتخاب ستون‌ها
        columns_to_display = ["Itemcode", "Description", "QUANTITY", "LENGTH(M)"]

        tree = ttk.Treeview(top, columns=columns_to_display, show="headings")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for col in columns_to_display:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor='center')

        for _, row in mto_items.iterrows():
            values = [row.get(col, "") for col in columns_to_display]
            tree.insert("", tk.END, values=values)

        ttk.Button(top, text="بستن", command=top.destroy).pack(pady=5)

    def export_excel(self):
        if not self.registry:
            self.console_output("⚠️ لطفاً ابتدا پروژه را بارگذاری کنید.")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
        if filepath:
            try:
                self.registry.export_to_excel(filepath)
                self.console_output(f"✅ فایل با موفقیت ذخیره شد:\n{filepath}")
            except Exception as e:
                self.console_output(f"❌ خطا در خروجی گرفتن:\n{e}")

    def create_menu(self):
        menubar = tk.Menu(self)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="درباره", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def show_about(self):
        messagebox.showinfo("درباره", "نرم‌افزار مدیریت MIV\nساخته شده توسط H.IZADI")


if __name__ == "__main__":
    from miv_registry import MIVRegistry

    # یک پروژه تستی یا پیش‌فرض بده اینجا، مثلا P01
    registry = MIVRegistry("P01")
    app = MIVApp(registry)
    app.mainloop()

