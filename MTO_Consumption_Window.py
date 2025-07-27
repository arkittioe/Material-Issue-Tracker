import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class MTOConsumptionWindow(tk.Toplevel):

    def __init__(self, master, registry, line_no, project, callback):
        super().__init__(master)
        self.registry = registry
        self.line_no = line_no
        self.project = project
        self.callback = callback  # تابعی که خلاصه نهایی رو بفرسته

        self.title(f"انتخاب آیتم‌های مصرفی برای خط {line_no}")
        self.geometry("800x500")
        self.configure(bg="white")

        self.entries = {}  # {Itemcode: Entry برای مقدار مصرف}

        # گرفتن آیتم‌های MTO
        self.mto_items = self.registry.get_mto_items(line_no)
        if self.mto_items.empty:
            messagebox.showerror("خطا", f"MTO برای خط {line_no} یافت نشد.")
            self.destroy()
            return

        self.create_widgets()

    def create_widgets(self):
        self.configure(bg="white")

        lbl = tk.Label(self, text="مقدار مصرف از آیتم‌های زیر را وارد کنید:",
                       font=("Tahoma", 12, "bold"), bg="white", anchor="w")
        lbl.pack(pady=(15, 5), padx=10, anchor="w")

        columns = ["Item Code", "Description", "Unit", "Total Qty", "Used", "Remaining", "Consume", "Use All"]
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Tahoma", 10, "bold"))
        style.configure("Treeview", font=("Tahoma", 10), rowheight=30)

        for col in columns:
            self.tree.heading(col, text=col)
            width = 250 if col == "Description" else 100
            self.tree.column(col, width=width, anchor=tk.W)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.entries = {}
        self.use_all_vars = {}

        for idx, row in self.mto_items.iterrows():
            itemcode = str(row.get("Itemcode", "")).strip()
            desc = str(row.get("Description", "")).strip()
            unit = str(row.get("UNIT", "")).strip()

            key = self.get_key(row)

            type_value = str(row.get("Type", "")).strip().lower().replace(" ", "")
            try:
                if "pipe" in type_value:
                    total_qty = float(row.get("LENGTH(M)", 0) or 0)
                else:
                    total_qty = float(row.get("QUANTITY", 0) or 0)
            except (ValueError, TypeError):
                total_qty = 0.0

            used = self.registry.get_used_qty(self.project, self.line_no, itemcode, desc)

            remaining = max(0, total_qty - used)

            entry_var = tk.StringVar()
            self.entries[key] = (entry_var, remaining, unit, desc)

            use_all_display = "✔️" if remaining == 0 else ""

            self.tree.insert(
                "", "end", iid=key,
                values=(itemcode, desc, unit, total_qty, used, remaining, "", use_all_display)
            )

            var = tk.BooleanVar()
            self.use_all_vars[key] = var

        self.tree.bind("<Double-1>", self.on_double_click_entry)
        self.tree.bind("<Button-1>", self.on_tree_click)


        btn = tk.Button(self, text="تایید و ادامه", bg="#28a745", fg="white",
                        font=("Tahoma", 11, "bold"), command=self.on_confirm)
        btn.pack(pady=15)

    def on_confirm(self):
        summary_parts = []
        updates = []

        for key, (entry, remaining, unit, desc) in self.entries.items():
            val = entry.get().strip()
            if not val:
                continue

            try:
                qty = float(val)
                if qty <= 0 or qty > remaining:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("خطا", f"مقدار نامعتبر برای {key}. باید بین 0 و {remaining} باشد.")
                return

            # تشخیص اینکه آیا key مربوط به Itemcode هست یا Description
            use_desc = not key or key.lower() == "nan" or key == desc

            updates.append((
                "" if use_desc else key,  # اگر باید از Description استفاده بشه، Itemcode خالی می‌گذاریم
                qty,
                unit,
                desc
            ))

            # ساخت خلاصه مصرف
            if unit.lower() in ['m', 'meter', 'mtr']:
                summary_parts.append(f"{qty}m {desc if use_desc else key}")
            else:
                summary_parts.append(f"{int(qty)}x{desc if use_desc else key}")

        if not updates:
            messagebox.showwarning("هشدار", "هیچ آیتمی انتخاب نشده است.")
            return

        # ذخیره در فایل MTO_PROGRESS
        self.registry.update_progress_file(self.project, self.line_no, updates)

        # ساخت خلاصه و ارسال به کال‌بک
        summary = ", ".join(summary_parts)
        self.callback(summary)
        self.destroy()

    def on_double_click_entry(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]

        # گرفتن آیتم‌کد و توضیح برای عنوان پنجره
        values = self.tree.item(iid)["values"]
        itemcode = values[0] if values else ""
        desc = values[1] if len(values) > 1 else ""

        title_text = f"مقدار مصرف برای {itemcode if itemcode.strip() else desc}"

        entry_popup = tk.Toplevel(self)
        entry_popup.title(title_text)
        entry_popup.geometry("300x120")
        entry_popup.grab_set()

        tk.Label(entry_popup, text="مقدار مصرف:", font=("Tahoma", 11)).pack(pady=10)
        entry = ttk.Entry(entry_popup, font=("Tahoma", 11))
        entry.pack()
        entry.focus()

        # اگر مقدار قبلی وجود داشت در ورودی قرار بده
        prev_val = self.entries.get(iid, (None,))[0]
        if prev_val:
            entry.insert(0, prev_val.get())

        def confirm():
            qty = entry.get().strip()

            # اعتبارسنجی ساده مقدار وارد شده
            try:
                val = float(qty)
                if val < 0:
                    raise ValueError
            except:
                messagebox.showerror("خطا", "مقدار وارد شده باید عدد مثبت باشد.")
                return

            # بروزرسانی ستون Consume در جدول و مقدار ورودی در self.entries
            self.tree.set(iid, column="Consume", value=qty)
            self.entries[iid][0].set(qty)

            # به‌روزرسانی ستون Use All بر اساس مقدار وارد شده و باقی‌مانده
            remaining = self.entries[iid][1]
            if val >= remaining:
                self.tree.set(iid, "Use All", "✔️")
            else:
                self.tree.set(iid, "Use All", "")

            entry_popup.destroy()

        tk.Button(entry_popup, text="تایید", command=confirm).pack(pady=10)

        print(self.entries.keys())
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]
        itemcode = self.tree.item(iid)["values"][0]

        entry_popup = tk.Toplevel(self)
        entry_popup.title(f"مقدار مصرف برای {itemcode}")
        entry_popup.geometry("300x120")
        entry_popup.grab_set()

        tk.Label(entry_popup, text="مقدار مصرف:", font=("Tahoma", 11)).pack(pady=10)
        entry = ttk.Entry(entry_popup, font=("Tahoma", 11))
        entry.pack()
        entry.focus()

        def confirm():

            qty = entry.get().strip()
            self.tree.set(iid, column="Consume", value=qty)
            key = iid  # چون iid همان کلیدی است که در self.entries استفاده شده
            self.entries[key][0].set(qty)

            entry_popup.destroy()

        tk.Button(entry_popup, text="تایید", command=confirm).pack(pady=10)

    def set_full_qty(self, itemcode):
        var, remaining, _, _ = self.entries[itemcode]
        if self.use_all_vars[itemcode].get():
            var.set(str(remaining))
            self.tree.set(itemcode, column="Consume", value=str(remaining))
            print(
                f"[DEBUG] itemcode: {itemcode}, remaining: {remaining}, checkbox: {self.use_all_vars[itemcode].get()}")

        else:
            var.set("")
            self.tree.set(itemcode, column="Consume", value="")

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        col_index = int(col[1:]) - 1  # تبدیل '#8' به 7

        # نام ستون‌ها باید با ترتیب ستون‌ها تطابق داشته باشه
        if self.tree["columns"][col_index] == "Use All":
            current_val = self.tree.set(row_id, "Use All")

            if current_val == "✔️":
                # حذف انتخاب Use All
                self.tree.set(row_id, "Use All", "")
                self.tree.set(row_id, "Consume", "")
                self.entries[row_id][0].set("")
            else:
                # انتخاب Use All و مقداردهی کامل به Consume
                remaining = self.entries[row_id][1]
                self.tree.set(row_id, "Use All", "✔️")
                self.tree.set(row_id, "Consume", str(remaining))
                self.entries[row_id][0].set(str(remaining))

    def get_key(self, row):
        itemcode = str(row.get("Itemcode", "")).strip()
        if not itemcode or itemcode.lower() == "nan":
            return str(row.get("Description", "")).strip()
        return itemcode

