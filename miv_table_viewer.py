# miv_table_viewer.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd

try:
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
except ImportError:
    # اگر reportlab نصب نیست، خروجی PDF غیرفعال می‌شود و پیام خطا هنگام اجرا داده خواهد شد.
    pass


class MIVTableViewer(tk.Toplevel):
    def __init__(self, master, registry, mode, project, line_no=None, last_n=None, filters=None):
        """
        # master: پنجره والد
        # registry: نمونه کلاس رجیستری برای خواندن داده‌ها
        # mode: نوع داده‌ای که نمایش داده می‌شود ('last', 'miv', 'all', 'complete', 'incomplete', 'mto')
        # project: کد پروژه (مثلاً 'P02')
        # line_no: شماره خط (در صورت نیاز)
        # last_n: تعداد آخرین رکوردها (برای حالت 'last')
        """
        super().__init__(master)
        self.registry = registry
        self.mode = mode
        self.project = project
        self.line_no = line_no
        self.last_n = last_n

        self.title(f"MIV Table Viewer - {project}")
        self.geometry("900x600")
        self.configure(bg="white")

        self.create_widgets()
        self.load_data()
        self.filters = filters or {}

    def create_widgets(self):
        # Frame برای جدول و اسکرول بارها
        frame = ttk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ایجاد Treeview با ستون‌های داینامیک (بعداً تنظیم می‌شود)
        self.tree = ttk.Treeview(frame, columns=[], show='headings')
        self.tree.grid(row=0, column=0, sticky="nsew")

        # اسکرول بار عمودی
        scrollbar_v = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_v.grid(row=0, column=1, sticky='ns')

        # اسکرول بار افقی
        scrollbar_h = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        scrollbar_h.grid(row=1, column=0, sticky='ew')

        self.tree.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)

        # پیکربندی شبکه‌ای برای رشد صحیح جدول و اسکرول‌ها
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # دکمه‌ها در پایین پنجره
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        self.btn_export_excel = tk.Button(btn_frame, text="خروجی اکسل", command=self.export_to_excel)
        self.btn_export_excel.pack(side=tk.LEFT, padx=5)

        self.btn_export_pdf = tk.Button(btn_frame, text="خروجی PDF", command=self.export_to_pdf)
        self.btn_export_pdf.pack(side=tk.LEFT, padx=5)

        self.btn_close = tk.Button(btn_frame, text="بستن پنجره", command=self.destroy)
        self.btn_close.pack(side=tk.RIGHT, padx=5)

    def load_data(self):
        # گرفتن داده از رجیستری با توجه به mode
        try:
            if self.mode == "last":
                df = self.registry.get_miv_data(self.project, last_n=self.last_n)
            elif self.mode == "miv":
                df = self.registry.get_miv_data(self.project, line_no=self.line_no)
            elif self.mode == "all":
                df = self.registry.get_miv_data(self.project)
            elif self.mode == "complete":
                df = self.registry.get_miv_data(self.project, filter_type="complete")
            elif self.mode == "incomplete":
                df = self.registry.get_miv_data(self.project, filter_type="incomplete")
            elif self.mode == "mto":
                df = self.registry.get_mto_data(self.project, self.line_no)
            elif self.mode == "custom_filter":
                df = self.registry.get_miv_data(self.project)  # گرفتن همه داده‌ها
                for col, val in self.filters.items():
                    df = df[df[col].astype(str).str.lower() == val.lower()]
            else:
                df = pd.DataFrame()



            if df.empty:
                messagebox.showinfo("اطلاع", "داده‌ای برای نمایش وجود ندارد.")
                return


            self.show_dataframe(df)


        except Exception as e:
            messagebox.showerror("خطا در بارگذاری داده", str(e))

    def show_dataframe(self, df: pd.DataFrame):
        # تنظیم ستون‌ها بر اساس داده
        self.tree.delete(*self.tree.get_children())  # پاک کردن داده قبلی
        self.tree["columns"] = list(df.columns)

        for col in df.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.W)

        # اضافه کردن داده‌ها به جدول
        for _, row in df.iterrows():
            self.tree.insert("", tk.END, values=list(row))

    def export_to_excel(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if not file_path:
            return

        # گرفتن داده فعلی از جدول برای ذخیره
        cols = self.tree["columns"]
        data = [self.tree.item(item)["values"] for item in self.tree.get_children()]
        df = pd.DataFrame(data, columns=cols)

        try:
            df.to_excel(file_path, index=False)
            messagebox.showinfo("موفقیت", f"فایل اکسل با موفقیت ذخیره شد:\n{file_path}")
        except Exception as e:
            messagebox.showerror("خطا در ذخیره فایل", str(e))

    def export_to_pdf(self):
        # چک کردن وجود reportlab
        try:
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_LEFT
        except ImportError:
            messagebox.showerror("خطا", "لطفاً ابتدا پکیج reportlab را نصب کنید:\npip install reportlab")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not file_path:
            return

        # گرفتن داده‌های جدول
        cols = self.tree["columns"]
        data = [self.tree.item(item)["values"] for item in self.tree.get_children()]
        df = pd.DataFrame(data, columns=cols)

        try:
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            elements = []

            styles = getSampleStyleSheet()
            title = Paragraph(f"<b>گزارش {self.mode.upper()} - پروژه: {self.project}</b>", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 12))

            wrap_style = ParagraphStyle(
                name='WrappedCell',
                fontName='Helvetica',
                fontSize=8,
                leading=10,
                alignment=TA_LEFT
            )

            # ساخت داده‌های جدول به شکل پاراگراف با wrap
            table_data = [[Paragraph(str(col), wrap_style) for col in df.columns]]
            for row in df.itertuples(index=False):
                table_data.append([Paragraph(str(cell), wrap_style) for cell in row])

            page_width = A4[0] - 2 * 40  # حاشیه 40 از دو طرف
            num_cols = len(df.columns)
            col_widths = []

            for col in df.columns:
                if "item" in col.lower():
                    col_widths.append(100)
                else:
                    col_widths.append((page_width - 100) / (num_cols - 1))

            pdf_table = Table(table_data, colWidths=col_widths, repeatRows=1)

            pdf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))

            elements.append(pdf_table)
            doc.build(elements)
            messagebox.showinfo("موفقیت", f"فایل PDF با موفقیت ذخیره شد:\n{file_path}")

        except Exception as e:
            messagebox.showerror("خطا در ساخت PDF", str(e))
