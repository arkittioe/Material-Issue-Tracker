import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import pandas as pd
from datetime import datetime
import os

class EditMIVWindow(tk.Toplevel):
    def __init__(self, master, registry, line_no, project):
        super().__init__(master)
        self.registry = registry
        self.line_no = line_no
        self.project = project
        self.title(f"ویرایش رکوردهای خط {line_no} در پروژه {project}")
        self.geometry("950x450")
        self.configure(bg="#1e1e1e")

        # خواندن فایل پروژه
        self.df = self.registry.read_project_df(project)

        # بررسی وجود رکورد برای خط مورد نظر
        self.records = self.df[self.df["Line No"] == line_no]
        if self.records.empty:
            messagebox.showwarning("هشدار", f"خط {line_no} در پروژه {project} یافت نشد.")
            self.destroy()
            return

        # ساخت جدول
        self.tree = ttk.Treeview(self, columns=self.registry.HEADERS, show='headings', style="Custom.Treeview")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # تنظیم استایل جدول (دارک)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Custom.Treeview",
                        background="#2b2b2b",
                        fieldbackground="#2b2b2b",
                        foreground="white",
                        rowheight=28,
                        font=("Tahoma", 11))
        style.configure("Custom.Treeview.Heading", background="#444", foreground="white", font=("Tahoma", 11, "bold"))

        # افزودن ستون‌ها
        for col in self.registry.HEADERS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        # درج رکوردها
        for idx, row in self.records.iterrows():
            values = [row.get(col, "") for col in self.registry.HEADERS]
            self.tree.insert("", "end", iid=str(idx), values=values)

        # اسکرول‌بار عمودی
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)

        # ویرایش با دابل‌کلیک
        self.tree.bind("<Double-1>", self.on_double_click)

        # دکمه ذخیره
        self.save_btn = tk.Button(self, text="💾 ذخیره تغییرات", command=self.save_changes,
                                  font=("Tahoma", 11), bg="#007acc", fg="white")
        self.save_btn.pack(pady=10)

    def on_double_click(self, event):
        item = self.tree.selection()
        if not item:
            return
        item = item[0]
        col = self.tree.identify_column(event.x)
        col_idx = int(col.replace('#', '')) - 1
        col_name = self.registry.HEADERS[col_idx]

        old_value = self.tree.set(item, col_name)
        new_value = simpledialog.askstring("ویرایش مقدار", f"{col_name}:", initialvalue=old_value, parent=self)
        if new_value is not None:
            self.tree.set(item, col_name, new_value)

    def save_changes(self):
        moved_records = {}  # دیکشنری برای ذخیره رکوردهایی که باید به پروژه دیگر منتقل شوند

        for iid in self.tree.get_children():
            values = self.tree.item(iid)["values"]
            updated_record = {col: values[idx] for idx, col in enumerate(self.registry.HEADERS)}
            original_project = self.df.at[int(iid), "Project"]
            new_project = updated_record["Project"]

            if new_project != original_project:
                # اضافه کردن رکورد به پروژه جدید
                if new_project not in moved_records:
                    moved_records[new_project] = []
                moved_records[new_project].append(updated_record)

                # حذف رکورد از پروژه فعلی
                self.df.drop(index=int(iid), inplace=True)
            else:
                # فقط آپدیت رکورد در پروژه فعلی
                for col_idx, col_name in enumerate(self.registry.HEADERS):
                    self.df.at[int(iid), col_name] = values[col_idx]

        # ذخیره تغییرات در فایل پروژه فعلی
        self.df.to_csv(self.registry.csv_file, index=False)

        # ذخیره رکوردهای منتقل‌شده در پروژه‌های جدید
        for target_project, records in moved_records.items():
            target_path = self.registry.csv_path(target_project)
            if os.path.exists(target_path):
                target_df = pd.read_csv(target_path)
            else:
                target_df = pd.DataFrame(columns=self.registry.HEADERS)
            new_df = pd.DataFrame(records)
            target_df = pd.concat([target_df, new_df], ignore_index=True)
            target_df.to_csv(target_path, index=False)

        messagebox.showinfo("موفقیت", "تغییرات با موفقیت ذخیره شد.")
        self.destroy()

class DeleteMIVWindow(tk.Toplevel):
    def __init__(self, master, registry, line_no, project):
        super().__init__(master)
        self.registry = registry
        self.line_no = line_no
        self.project = project
        self.title(f"حذف رکوردهای خط {line_no} در پروژه {project}")
        self.geometry("950x450")
        self.configure(bg="#1e1e1e")

        # خواندن فایل پروژه
        self.df = self.registry.read_project_df(project)

        # گرفتن رکوردهای مرتبط با خط مورد نظر
        self.records = self.df[self.df["Line No"] == line_no]
        if self.records.empty:
            messagebox.showwarning("هشدار", f"هیچ رکوردی برای خط {line_no} یافت نشد.")
            self.destroy()
            return

        # جدول
        self.tree = ttk.Treeview(self, columns=self.registry.HEADERS, show='headings', style="Custom.Treeview")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # استایل جدول دارک
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Custom.Treeview",
                        background="#2b2b2b",
                        fieldbackground="#2b2b2b",
                        foreground="white",
                        rowheight=28,
                        font=("Tahoma", 11))
        style.configure("Custom.Treeview.Heading",
                        background="#444",
                        foreground="white",
                        font=("Tahoma", 11, "bold"))

        # تنظیم ستون‌ها
        for col in self.registry.HEADERS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        # درج رکوردها
        for idx, row in self.records.iterrows():
            values = [row.get(col, "") for col in self.registry.HEADERS]
            self.tree.insert("", "end", iid=str(idx), values=values)

        # اسکرول‌بار
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)

        # دکمه حذف
        self.delete_btn = tk.Button(self, text="🗑️ حذف رکورد انتخاب‌شده", command=self.delete_selected,
                                    font=("Tahoma", 11), bg="#e74c3c", fg="white")
        self.delete_btn.pack(pady=10)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("هشدار", "هیچ رکوردی انتخاب نشده است.")
            return

        if not messagebox.askyesno("تأیید حذف", "آیا از حذف رکورد انتخاب‌شده مطمئن هستید؟"):
            return

        for iid in selected:
            self.df.drop(index=int(iid), inplace=True)
            self.tree.delete(iid)

        # ذخیره تغییرات در فایل CSV
        self.df.to_csv(self.registry.csv_file, index=False)

        messagebox.showinfo("موفقیت", "رکورد با موفقیت حذف شد.")
        self.destroy()




