import os
import csv
import jdatetime
import pandas as pd
from datetime import datetime
import glob
import shutil
import re
import difflib

class MIVRegistry:
    HEADERS = [
        "Project", "Line No", "MIV Tag", "Location", "Status", "Comment",
        "Registered For", "Registered By", "Last Updated (Shamsi)", "Complete"
    ]


    def __init__(self, project, project_dir="."):
        self.project = project.upper()
        self.project_dir = project_dir
        self.csv_file = os.path.join(self.project_dir, f"{self.project}.csv")

        # ✅ حالا به صورت صریح فیلدهای مورد استفاده را مشخص می‌کنیم
        self.fieldnames = MIVRegistry.HEADERS

        self.ensure_csv_exists()
        self.ensure_csv_headers()
        self.mto_df = pd.DataFrame()
        self.load_mto()

    @property
    def current_project(self):
        return self.project

    def ensure_csv_exists(self):
        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir)

        if not os.path.isfile(self.csv_file):
            with open(self.csv_file, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writeheader()

    def ensure_csv_headers(self):
        if os.path.exists(self.csv_file):
            df = pd.read_csv(self.csv_file)
            missing_cols = [col for col in self.HEADERS if col not in df.columns]
            if missing_cols:
                print(f"⚠️ ستون‌های زیر در فایل CSV نبودند و اضافه می‌شوند: {missing_cols}")
                for col in missing_cols:
                    df[col] = ""
                df.to_csv(self.csv_file, index=False)

    def get_shamsi_date(self):
        return jdatetime.date.today().strftime('%Y/%m/%d')

    def is_duplicate_miv(self, miv_tag):
        df = pd.read_csv(self.csv_file)
        return any(df["MIV Tag"] == miv_tag)

    def get_existing_line_info(self, line_no):
        df = pd.read_csv(self.csv_file)
        match = df[df["Line No"] == line_no]
        return match.iloc[0].to_dict() if not match.empty else None

    def save_record(self, data):
        with open(self.csv_file, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(data)

    def search_and_edit(self):
        line_no = input("🔍 Line No برای ویرایش: ").strip()
        df = pd.read_csv(self.csv_file)
        matches = df[df["Line No"] == line_no]

        if matches.empty:
            print("❌ رکوردی یافت نشد.")
            return

        if len(matches) == 1:
            index = matches.index[0]
        else:
            print(f"⚠️ چند رکورد با Line No = {line_no} یافت شد:")
            for i, (_, row) in enumerate(matches.iterrows(), start=1):
                # نمایش خلاصه رکوردها با شماره انتخاب
                print(f"{i}) MIV Tag: {row['MIV Tag']} | Location: {row['Location']} | Status: {row['Status']}")

            choice = input(f"عدد ردیف مورد نظر برای ویرایش را وارد کنید (1 تا {len(matches)}): ").strip()
            if not choice.isdigit() or not (1 <= int(choice) <= len(matches)):
                print("❌ انتخاب نامعتبر.")
                return
            index = matches.index[int(choice) - 1]

        original_row = df.loc[index].copy()
        updated_row = original_row.copy()

        print("\n🔎 رکورد انتخاب شده برای ویرایش:")
        print(original_row)

        confirm = input("✏️ آیا مایل به ویرایش هستید؟ (y/n): ").lower()
        if confirm != 'y':
            return

        for col in self.HEADERS[:-1]:
            new_val = input(f"{col} (فعلی: {df.at[index, col]}): ").strip()
            if new_val:
                updated_row[col] = new_val

        updated_row["Last Updated (Shamsi)"] = self.get_shamsi_date()

        if updated_row["Project"].upper() != self.project:
            df = df.drop(index)
            df.to_csv(self.csv_file, index=False)

            new_project = updated_row["Project"].upper()
            new_registry = MIVRegistry(new_project)
            new_registry.save_record(updated_row.values.tolist())
            print(f"✅ رکورد به پروژه {new_project} منتقل شد.")
        else:
            for col in self.HEADERS:
                df.at[index, col] = updated_row[col]
            df.to_csv(self.csv_file, index=False)
            print("✅ رکورد با موفقیت ویرایش شد.")

    # def is_line_miv_complete(self, line_no):
    #     df = pd.read_csv(self.csv_file)
    #     if "Complete" not in df.columns:
    #         return False
    #     complete_series = df["Complete"].astype(str).str.strip().str.lower()
    #     match = df[(df["Line No"] == line_no) & (complete_series == "true")]
    #     return not match.empty

    def export_to_excel(self, filepath=None):
        try:
            df = pd.read_csv(self.csv_file)
            if not filepath:
                date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                filepath = f"{self.project}_export_{date_str}.xlsx"
            df.to_excel(filepath, index=False)
            print(f"✅ فایل با موفقیت ذخیره شد: {filepath}")
        except Exception as e:
            print(f"❌ خطا در خروجی گرفتن: {e}")

    def register_miv(self, line_no, miv_tag, location, status, comment):
        if self.is_duplicate_miv(miv_tag):
            print(f"❌ این MIV Tag قبلاً ثبت شده: {miv_tag}")
            return False

        existing_line = self.get_existing_line_info(line_no)
        if existing_line:
            print("⚠️ این Line قبلاً ثبت شده:")
            for k, v in existing_line.items():
                print(f"  {k}: {v}")
            # فرض کنیم تست اتوماتیک، اجازه ادامه ثبت را می‌دهد
            # یا اینجا می‌توانم پارامتر برای تایید اضافه کنم

        shamsi = self.get_shamsi_date()

        self.save_record([
            self.project, line_no, miv_tag, location,
            status, comment, "", "", shamsi, "False"
        ])

        print("✅ MIV با موفقیت ثبت شد.")
        return True

    def search_record(self, line_no):
        df = pd.read_csv(self.csv_file)
        miv_records = df[df["Line No"] == line_no]
        mto_items = self.get_mto_items(line_no)
        complete = self.is_line_miv_complete(line_no)
        return miv_records, mto_items, complete

    def load_mto(self):
        mto_filename = f"MTO-{self.project}.csv"
        if os.path.exists(mto_filename):
            self.mto_df = pd.read_csv(mto_filename)
        else:
            self.mto_df = pd.DataFrame()

    def get_mto_items(self, line_no):
        if self.mto_df.empty:
            return pd.DataFrame()

        norm_input = self.normalize_line_no(line_no)
        return self.mto_df[self.mto_df["Line No"].apply(lambda x: self.normalize_line_no(x) == norm_input)]

    def delete_line(self, line_no, project):
        df = self.read_project_df(project)
        if df.empty:
            raise ValueError(f"No records found in project {project}")
        original_len = len(df)
        df = df[df["Line No"] != line_no]
        if len(df) == original_len:
            raise ValueError(f"Line No {line_no} not found in project {project}")
        self.save_project_df(project, df)

    def edit_line(self, line_no, project, updated_data: dict):
        df = self.read_project_df(project)
        if line_no not in df["Line No"].values:
            raise ValueError(f"Line No {line_no} not found in project {project}")
        df.loc[df["Line No"] == line_no, updated_data.keys()] = list(updated_data.values())
        self.save_project_df(project, df)

    def move_line(self, line_no, from_project, to_project):
        df_from = self.read_project_df(from_project)
        df_to = self.read_project_df(to_project)
        if line_no not in df_from["Line No"].values:
            raise ValueError(f"Line No {line_no} not found in {from_project}")
        row = df_from[df_from["Line No"] == line_no]
        df_from = df_from[df_from["Line No"] != line_no]
        df_to = pd.concat([df_to, row], ignore_index=True)
        self.save_project_df(from_project, df_from)
        self.save_project_df(to_project, df_to)

    def copy_line(self, line_no, from_project, to_project):
        df_from = self.read_project_df(from_project)
        df_to = self.read_project_df(to_project)
        if line_no not in df_from["Line No"].values:
            raise ValueError(f"Line No {line_no} not found in {from_project}")
        row = df_from[df_from["Line No"] == line_no]
        df_to = pd.concat([df_to, row], ignore_index=True)
        self.save_project_df(to_project, df_to)

    def rename_project(self, old_name, new_name):
        old_path = self.csv_path(old_name)
        new_path = self.csv_path(new_name)
        if not os.path.exists(old_path):
            raise FileNotFoundError(f"Project {old_name} does not exist.")
        if os.path.exists(new_path):
            raise FileExistsError(f"Project {new_name} already exists.")
        os.rename(old_path, new_path)

    def list_projects(self):
        pattern = os.path.join(self.project_dir, "*.csv")
        return [os.path.splitext(os.path.basename(f))[0] for f in glob.glob(pattern)]

    def export_project_to_excel(self, project, path):
        df = self.read_project_df(project)
        df.to_excel(path, index=False)

    def read_project_df(self, project):
        """فقط و فقط پروژه مشخص‌شده رو بخونه و اگر ندادیم، خطا بده"""
        if not project:
            raise ValueError("❌ نام پروژه مشخص نشده است.")

        path = self.csv_path(project)
        if os.path.exists(path):
            return pd.read_csv(path)
        else:
            print(f"⚠️ فایل پروژه {project} موجود نیست.")
            return pd.DataFrame()

    def export_miv_line_to_excel(self, line_no, project, path):
        df = self.read_project_df(project)
        if line_no not in df["Line No"].values:
            raise ValueError(f"Line No {line_no} not found in project {project}")
        record = df[df["Line No"] == line_no]
        record.to_excel(path, index=False)

    def check_duplicates(self, project):
        df = self.read_project_df(project)
        return df[df.duplicated(subset=["Line No"], keep=False)]

    def reset_project(self, project):
        path = self.csv_path(project)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Project {project} does not exist.")
        df = pd.DataFrame(columns=self.HEADERS)
        df.to_csv(path, index=False)

    def lock_project(self, project):
        path = self.csv_path(project) + ".lock"
        with open(path, "w") as f:
            f.write("locked")

    def unlock_project(self, project):
        path = self.csv_path(project) + ".lock"
        if os.path.exists(path):
            os.remove(path)

    def is_project_locked(self, project):
        return os.path.exists(self.csv_path(project) + ".lock")

    def csv_path(self, project=None):
        if project is None:
            project = self.project
        return os.path.abspath(f"{project.upper()}.csv")

    def create_project(self, project_code):
        try:
            csv_file = self.get_csv_file(project_code)
            if not os.path.exists(csv_file):
                df = pd.DataFrame(columns=self.HEADERS)
                df.to_csv(csv_file, index=False)
                return True, f"✅ پروژه {project_code} با موفقیت ایجاد شد."
            else:
                return False, f"⚠️ پروژه {project_code} قبلاً وجود دارد."
        except Exception as e:
            return False, f"❌ خطا در ایجاد پروژه: {str(e)}"

    def delete_project(self, project_code):
        try:
            csv_file = self.get_csv_file(project_code)
            if os.path.exists(csv_file):
                os.remove(csv_file)
                return True, f"✅ پروژه {project_code} با موفقیت حذف شد."
            else:
                return False, f"⚠️ پروژه {project_code} یافت نشد."
        except Exception as e:
            return False, f"❌ خطا در حذف پروژه: {str(e)}"

    def save_project_df(self, project, df):
        path = self.csv_path(project)
        df.to_csv(path, index=False)

    def get_csv_file(self, project_code):
        return os.path.join(self.project_dir, f"{project_code}.csv")

    # برای استفاده توی miv_table_viewer

    def get_miv_data(self, project, filter_type=None, line_no=None, last_n=None):
        """
        گرفتن داده‌های MIV با فیلترهای مختلف:
        - filter_type: 'complete' یا 'incomplete'
        - line_no: شماره خط خاص
        - last_n: آخرین n رکورد
        """
        df = self.read_project_df(project)

        if line_no:
            df = df[df["Line No"].astype(str) == str(line_no)]

        if filter_type == "complete":
            df = df[df["Status"].str.lower() == "done"]
        elif filter_type == "incomplete":
            df = df[df["Status"].str.lower() != "done"]

        if last_n:
            df = df.tail(last_n)

        return df

    # برای استفاده توی miv_table_viewer

    def get_mto_data(self, project, line_no):
        """
        گرفتن داده‌های MTO برای یک شماره خط خاص
        """
        df = self.load_mto(project)
        return df[df["Line No"].astype(str) == str(line_no)]

    def backup_project(self, project_code=None):
        try:
            if project_code is None or project_code.lower() == "all":
                # بک‌آپ همه پروژه‌ها
                files = [f for f in os.listdir(self.project_dir) if f.endswith(".csv")]
                if not files:
                    return False, "⚠️ هیچ فایل پروژه‌ای برای بک‌آپ وجود ندارد."

                now_str = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_dir = os.path.join(self.project_dir, f"backup_all_{now_str}")
                os.makedirs(backup_dir)

                for f in files:
                    src = os.path.join(self.project_dir, f)
                    dst = os.path.join(backup_dir, f)
                    shutil.copy2(src, dst)

                return True, f"✅ تمام پروژه‌ها در پوشه {backup_dir} بک‌آپ گرفته شدند."

            else:
                # بک‌آپ یک پروژه مشخص
                project_code = project_code.upper()
                src_file = os.path.join(self.project_dir, f"{project_code}.csv")

                if not os.path.exists(src_file):
                    return False, f"❌ فایل پروژه {project_code} یافت نشد."

                now_str = datetime.now().strftime("%Y%m%d-%H%M%S")
                backup_name = f"{project_code}_backup_{now_str}.csv"
                backup_path = os.path.join(self.project_dir, backup_name)

                shutil.copy2(src_file, backup_path)

                return True, f"✅ فایل بک‌آپ پروژه {project_code} در مسیر {backup_name} ذخیره شد."

        except Exception as e:
            return False, f"❌ خطا در تهیه بک‌آپ: {e}"

    def read_all_projects_df(self, data_type="miv"):
        """
        خواندن داده‌های همه پروژه‌ها در یک DataFrame
        data_type: "miv" یا "mto"
        """
        dfs = []
        pattern = "*.csv"
        for file_path in glob.glob(os.path.join(self.project_dir, pattern)):
            project_name = os.path.splitext(os.path.basename(file_path))[0]
            df = pd.read_csv(file_path)
            # فیلتر کردن بر اساس نوع داده (miv/mto) اگر لازم است
            # مثلا اگر فایل‌ها جدا هستند یا ستون‌ها متفاوت
            dfs.append(df)
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        else:
            return pd.DataFrame()

    def normalize_line_no(self, line_no):
        return re.sub(r'[\s,\-\'\"]', '', str(line_no)).lower()

    def suggest_line_no(self, line_no_input):
        """
        با استفاده از difflib نزدیک‌ترین شماره خط موجود در فایل MTO رو پیشنهاد میده.
        """
        mto_df = self.read_project_df(self.project)
        if "Line No" not in mto_df.columns:
            return None

        all_lines = mto_df["Line No"].dropna().unique().tolist()
        normalized_input = self.normalize_line_no(line_no_input)
        normalized_lines = {line: self.normalize_line_no(line) for line in all_lines}

        # جستجوی مشابه‌ترین مقدار
        best_match = None
        best_ratio = 0
        for original, normalized in normalized_lines.items():
            ratio = difflib.SequenceMatcher(None, normalized_input, normalized).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = original

        return best_match if best_ratio > 0.6 else None

    def get_all_line_no_suggestions(self, user_input, top_n=6):
        all_suggestions = []

        for project in self.list_projects():
            mto_path = os.path.join(self.project_dir, f"MTO-{project}.csv")
            if not os.path.exists(mto_path):
                continue

            mto_df = pd.read_csv(mto_path)
            if "Line No" not in mto_df.columns:
                continue

            norm_input = self.normalize_line_no(user_input)
            all_lines = mto_df["Line No"].dropna().unique()

            for line in all_lines:
                norm_line = self.normalize_line_no(str(line))
                score = 0.0

                if norm_input == norm_line:
                    score = 1.0
                six_digits = re.search(r'\d{6}', user_input)
                if six_digits and six_digits.group() in norm_line:
                    score += 0.8
                fuzzy = difflib.SequenceMatcher(None, norm_input, norm_line).ratio()
                score += fuzzy * 0.5

                if score > 0.5:
                    all_suggestions.append((score, str(line), project))

        # مرتب‌سازی بر اساس امتیاز
        top_matches = sorted(all_suggestions, key=lambda x: -x[0])[:top_n]
        return [(line, proj) for _, line, proj in top_matches]

    def get_used_qty(self, project, line_no, item_code):
        """
        مقدار استفاده‌شده از یک آیتم خاص در یک خط خاص رو از فایل MTO_PROGRESS می‌خونه.
        """
        progress_file = os.path.join(self.project_dir, f"MTO_PROGRESS-{project}.csv")
        if not os.path.exists(progress_file):
            return 0

        try:
            df = pd.read_csv(progress_file)
            match = df[(df["Line No"] == line_no) & (df["Item Code"] == item_code)]
            if not match.empty:
                return float(match.iloc[0]["Used Qty"])
        except Exception as e:
            print(f"⚠️ خطا در خواندن فایل پیشرفت: {e}")

        return 0

    def update_progress_file(self, project, line_no, updates):
        """
        updates: لیستی از تاپل‌ها [(item_code, used_qty, unit, desc), ...]
        """
        path = os.path.join(self.project_dir, f"MTO_PROGRESS-{project}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
        else:
            df = pd.DataFrame(columns=[
                "Line No", "Item Code", "Description", "Unit",
                "Total Qty", "Used Qty", "Remaining Qty", "Last Updated"
            ])

        mto_df = pd.read_csv(f"MTO-{project}.csv") if os.path.exists(f"MTO-{project}.csv") else pd.DataFrame()

        for item_code, qty, unit, desc in updates:
            total_qty = 0
            match = mto_df[(mto_df["Line No"] == line_no) & (mto_df["Itemcode"] == item_code)]
            if not match.empty:
                total_qty = float(match.iloc[0].get("QUANTITY", match.iloc[0].get("LENGTH(M)", 0)))

            current = df[(df["Line No"] == line_no) & (df["Item Code"] == item_code)]
            if not current.empty:
                idx = current.index[0]
                prev_used = float(df.at[idx, "Used Qty"])
                new_used = prev_used + qty
                df.at[idx, "Used Qty"] = new_used
                df.at[idx, "Remaining Qty"] = max(0, total_qty - new_used)
                df.at[idx, "Last Updated"] = self.get_shamsi_date()
            else:
                df = pd.concat([df, pd.DataFrame([{
                    "Line No": line_no,
                    "Item Code": item_code,
                    "Description": desc,
                    "Unit": unit,
                    "Total Qty": total_qty,
                    "Used Qty": qty,
                    "Remaining Qty": max(0, total_qty - qty),
                    "Last Updated": self.get_shamsi_date()
                }])], ignore_index=True)

        df.to_csv(path, index=False)

    def is_line_miv_complete(self, line_no):
        """
        بررسی می‌کند که آیا تمام آیتم‌های یک خط در فایل MTO مصرف شده‌اند یا نه.
        """
        progress_path = os.path.join(self.project_dir, f"MTO_PROGRESS-{self.project}.csv")
        if not os.path.exists(progress_path):
            return False

        try:
            df = pd.read_csv(progress_path)
            df_line = df[df["Line No"] == line_no]
            if df_line.empty:
                return False

            return all(df_line["Remaining Qty"] <= 0)
        except Exception as e:
            print(f"⚠️ خطا در بررسی وضعیت کامل شدن خط: {e}")
            return False
