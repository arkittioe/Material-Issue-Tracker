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
from reports_window import ReportsWindow
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import webbrowser


class MIVApp(tk.Tk):
    FIXED_PROJECTS = ["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P12", "P13", "P15"]
    PROJECT_LOCATIONS = {
        "P01": ["U106A"],
        "P02": ["U109A", "U109B"],
        "P03": ["U107A", ],
        # 👇 می‌تونی برای پروژه‌های دیگه هم اضافه کنی
        # "P04": ["..."]
    }

    def __init__(self, registry):
        super().__init__()
        self.registry = registry
        self.title("مدیریت MIV")
        self.geometry("1000x800")
        self.configure(bg="white")
        self.project_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.create_menu()
        self.create_widgets()  # ساخت ویجت‌ها
        self.console_output("✅ نرم‌افزار با موفقیت بارگذاری شد.")
        self.selected_line_no = None

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
        # --- Project Selection Frame ---
        frame_project = ttk.Frame(self)
        frame_project.grid(row=0, column=0, columnspan=2, pady=10, sticky="ew")

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)  # Give some weight to the dashboard row

        ttk.Label(frame_project, text="Project Scope:").pack(side=tk.LEFT, padx=5)
        self.project_combo = ttk.Combobox(frame_project, textvariable=self.project_var, state="readonly")
        self.project_combo['values'] = self.FIXED_PROJECTS
        self.project_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_project, text="Load Project", command=self.load_project).pack(side=tk.LEFT)

        # --- MIV Registration Form ---
        frame_form = ttk.LabelFrame(self, text="Register New MIV")
        frame_form.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        # ... (rest of your form code remains unchanged)
        labels = ["Line No", "MIV Tag", "Location", "Status", "Comment", "Registered For"]
        self.entries = {}
        for label in labels:
            row = ttk.Frame(frame_form)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label + ": ", width=15).pack(side=tk.LEFT)
            if label == "Line No":
                ent = LineNoAutocompleteEntry(row, self.registry)
                self.line_no_entry = ent  # ✅ ذخیره برای دسترسی بعدی

            elif label == "Comment":
                ent = ttk.Entry(row, state="readonly")
            elif label == "Location":
                ent = ttk.Combobox(row, state="readonly")
                self.location_combobox = ent  # ذخیره برای دسترسی در جاهای دیگر

            else:
                ent = ttk.Entry(row)
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.entries[label] = ent

        # 🟡 وقتی کاربر Line No رو پر می‌کنه و از فیلد خارج میشه، نمودار به‌روز بشه
        self.line_no_entry.bind("<FocusOut>", self.on_line_no_entered)

        row_rb = ttk.Frame(frame_form)
        row_rb.pack(fill=tk.X, pady=2)
        ttk.Label(row_rb, text="Registered By: ", width=15).pack(side=tk.LEFT)
        system_user = subprocess.check_output("whoami", shell=True).decode("utf-8").strip()
        lbl_rb = ttk.Label(row_rb, text=system_user, background="white", anchor="w", relief="sunken")
        lbl_rb.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entries["Registered By"] = lbl_rb
        ttk.Button(frame_form, text="Register Record", command=self.register_record).pack(pady=10)

        # --- Mini-Dashboard Frame ---
        frame_dashboard = ttk.LabelFrame(self, text="Project Dashboard")
        frame_dashboard.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        frame_dashboard.columnconfigure(0, weight=1)
        frame_dashboard.columnconfigure(1, weight=1)
        # ایجاد نمودار دایره‌ای در بالای داشبورد
        self.dashboard_fig = plt.Figure(figsize=(2.5, 2.5), dpi=100)
        self.dashboard_ax = self.dashboard_fig.add_subplot(111)
        self.dashboard_canvas = FigureCanvasTkAgg(self.dashboard_fig, master=frame_dashboard)
        self.dashboard_canvas.get_tk_widget().grid(row=0, column=0, columnspan=2, pady=5)

        # Project Progress Bar
        ttk.Label(frame_dashboard, text="Overall Progress:").grid(row=1, column=0, padx=5, pady=(0, 2), sticky="w")
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(frame_dashboard, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=2, column=0, padx=5, pady=2, sticky="ew")
        self.progress_label = ttk.Label(frame_dashboard, text="0%")
        self.progress_label.grid(row=2, column=1, padx=5, pady=2)

        # Button to open detailed reports
        ttk.Button(frame_dashboard, text="Open Detailed Reports...", command=self.open_reports_window) \
            .grid(row=3, column=0, columnspan=2, pady=10, sticky="s")

        # --- Search and Display Frame ---
        frame_search = ttk.LabelFrame(self, text="Search and Display")
        frame_search.grid(row=1, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")  # rowspan=2 to span both rows
        # ... (rest of your search frame code remains unchanged)
        row_search = ttk.Frame(frame_search)
        row_search.pack(fill=tk.X, pady=5)
        ttk.Label(row_search, text="Line No for Search: ", width=20).pack(side=tk.LEFT)
        self.search_entry = LineNoAutocompleteEntry(row_search, self.registry)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row_search, text="Search", command=self.search_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(row_search, text="Show MTO", command=self.show_mto_table).pack(side=tk.LEFT, padx=5)

        self.result_text = ConsoleText(frame_search, app=self, height=20, width=40)
        self.result_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # --- Bottom Buttons and Signature ---
        ttk.Button(self, text="Export to Excel", command=self.export_excel).grid(row=3, column=0, columnspan=2, pady=10)
        lbl_author = ttk.Label(self, text="H.IZADI", font=("Arial", 9), foreground="gray")
        lbl_author.grid(row=4, column=0, columnspan=2, pady=5, sticky="e")

    def create_chart_widgets(self):
        """ویجت‌های مربوط به نمایش نمودار را ایجاد می‌کند."""
        frame_charts = ttk.LabelFrame(self, text="📊 نمودار پیشرفت کل پروژه")
        # این فریم زیر فرم ثبت قرار میگیرد
        frame_charts.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

        # تنظیمات اولیه برای نمودار matplotlib
        self.fig = plt.Figure(figsize=(5, 4), dpi=100)
        self.fig.patch.set_facecolor('white')  # رنگ پس زمینه فیگور

        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('white')  # رنگ پس زمینه نمودار

        self.canvas = FigureCanvasTkAgg(self.fig, master=frame_charts)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.draw()

    def update_project_chart(self):
        """نمودار پیشرفت پروژه را بر اساس داده‌های جدید به‌روزرسانی می‌کند."""
        if not self.registry:
            return

        progress_data = self.registry.get_project_progress()
        completed = progress_data["completed"]
        total = progress_data["total"]

        if total == 0:
            self.ax.clear()
            self.ax.text(0.5, 0.5, "اطلاعات MTO برای این پروژه یافت نشد",
                         ha='center', va='center', fontsize=12, color='red')
            self.canvas.draw()
            return

        remaining = total - completed
        percentage = progress_data["percentage"]

        # داده‌ها برای نمودار دایره‌ای
        labels = [f'تکمیل شده ({completed})', f'باقی‌مانده ({remaining})']
        sizes = [completed, remaining]
        colors = ['#4CAF50', '#FF5722']  # سبز و نارنجی
        explode = (0.1, 0)  # برجسته کردن قطعه اول

        self.ax.clear()  # پاک کردن نمودار قبلی
        self.ax.pie(sizes, explode=explode, labels=labels, colors=colors,
                    autopct='%1.1f%%', shadow=True, startangle=140,
                    textprops={'fontsize': 10, 'fontname': 'Tahoma'})

        # اضافه کردن عنوان به نمودار
        self.ax.set_title(f"پروژه {self.registry.project} - پیشرفت: {percentage}%",
                          fontdict={'fontsize': 12, 'fontweight': 'bold', 'fontname': 'Tahoma'})

        self.ax.axis('equal')  # برای اطمینان از دایره‌ای بودن نمودار
        self.fig.tight_layout()  # تنظیم فاصله ها
        self.canvas.draw()

    def open_reports_window(self):
        """Opens the dedicated window for reports and charts."""
        if not self.registry:
            messagebox.showinfo("Info", "Please load a project first to provide context to the reports window.")
            # Even if no project is loaded, we can open the window.
            # The reports window will handle the logic.

        reports_win = ReportsWindow(self, self.registry)
        reports_win.grab_set()  # This makes the new window modal

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
            self.console_output("Please select a project.")
            return

        project_file = f"{project}.csv"
        if not os.path.exists(project_file):
            # ... (your existing code for creating a new project)
            answer = messagebox.askyesno("Project Not Found",
                                         f"Project file {project_file} not found. Create it?")
            if answer:
                created, msg = self.registry.create_project(project)
                self.console_output(msg)
            else:
                self.console_output(f"Project {project} was not loaded.")
                return

        self.registry = MIVRegistry(project)
        line_entry = self.entries.get("Line No")
        if isinstance(line_entry, LineNoAutocompleteEntry):
            line_entry.registry = self.registry

        self.console_output(f"Project {project} loaded successfully.")

        # ----> This is the new part to update the dashboard <----
        self.update_dashboard()
        # به‌روزرسانی مقادیر مجاز Location
        locations = self.PROJECT_LOCATIONS.get(project, [])
        if hasattr(self, "location_combobox"):
            self.location_combobox['values'] = locations
            self.location_combobox.set("")  # مقدار پیش‌فرض را خالی کن

    def on_line_no_entered(self, event=None):
        """وقتی Line No پر شد، نمودار مربوط به اون خط نمایش داده میشه"""
        if not self.registry:
            return

        line_no = self.line_no_entry.get().strip()
        if not line_no:
            return

        self.selected_line_no = line_no  # ✅ ذخیره شماره خط انتخاب‌شده
        self.update_dashboard()  # 🔁 به‌روزرسانی نمودار داشبورد

    def update_dashboard(self):
        """
        Refreshes the project dashboard: includes progress bar and per-line pie chart
        """
        if not self.registry or not self.registry.current_project:
            self.progress_var.set(0)
            self.progress_label.config(text="0%")

            if hasattr(self, "dashboard_ax"):
                self.dashboard_ax.clear()
                self.dashboard_ax.text(0.5, 0.5, "No project loaded", ha='center', va='center', fontsize=10)
                self.dashboard_canvas.draw()
            return

        # اگر خطی انتخاب نشده
        if not self.selected_line_no:
            self.progress_var.set(0)
            self.progress_label.config(text="0%")

            if hasattr(self, "dashboard_ax"):
                self.dashboard_ax.clear()
                self.dashboard_ax.text(0.5, 0.5, "No line selected", ha='center', va='center', fontsize=10)
                self.dashboard_canvas.draw()
            return

        # گرفتن پیشرفت خط
        progress_data = self.registry.get_line_progress(self.selected_line_no)
        total = progress_data.get("total_qty", 0)
        used = progress_data.get("used_qty", 0)
        percentage = progress_data.get("percentage", 0)
        remaining = total - used

        self.progress_var.set(percentage)
        self.progress_label.config(text=f"{percentage:.1f}%")

        if not hasattr(self, "dashboard_ax"):
            return

        self.dashboard_ax.clear()

        if total == 0:
            self.dashboard_ax.text(0.5, 0.5, "No data for this line", ha='center', va='center', fontsize=10)
        else:
            labels = [f"Used ({used})", f"Remaining ({remaining})"]
            sizes = [used, remaining]
            colors = ['#4CAF50', '#FF9800']
            explode = (0.1, 0)

            self.dashboard_ax.pie(
                sizes,
                explode=explode,
                labels=labels,
                colors=colors,
                autopct='%1.1f%%',
                shadow=True,
                startangle=90,
                textprops={'fontsize': 8, 'fontname': 'Tahoma'}
            )
            self.dashboard_ax.axis('equal')

        self.dashboard_fig.tight_layout()
        self.dashboard_canvas.draw()

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
        """Creates the main application menu."""
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        # The command to open the new window is linked here
        file_menu.add_command(label="Detailed Reports & Charts...", command=self.open_reports_window)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def open_reports_window(self):
        """Opens the dedicated window for detailed reports."""
        if not self.registry or not self.registry.current_project:
            messagebox.showinfo("Info", "Please load a project first.")
            return

        reports_win = ReportsWindow(self, self.registry)
        reports_win.grab_set()

    def show_about(self, event=None):  # <-- اینجا event رو اضافه کن
        import tkinter as tk
        import webbrowser

        about_win = tk.Toplevel()
        about_win.title("About")
        about_win.geometry("300x200")

        info_label = tk.Label(about_win, text="Material-Issue-Tracker Software\nCreated by H.IZADI", font=("Arial", 12))
        info_label.pack(pady=10)

        def open_github(event):
            webbrowser.open_new("https://github.com/arkittioe")

        github_link = tk.Label(about_win, text="GitHub: https://github.com/arkittioe/Material-Issue-Tracker", fg="blue", cursor="hand2",
                               font=("Arial", 10, "underline"))
        github_link.pack()
        github_link.bind("<Button-1>", open_github)


        close_btn = tk.Button(about_win, text="Close", command=about_win.destroy)
        close_btn.pack(pady=10)

if __name__ == "__main__":
    from miv_registry import MIVRegistry

    # یک پروژه تستی یا پیش‌فرض بده اینجا، مثلا P01
    registry = MIVRegistry("P01")
    app = MIVApp(registry)
    app.mainloop()

