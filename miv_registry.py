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

    def normalize_key(value):
        if pd.isna(value):
            return ""
        return str(value).strip().upper()

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

    def csv_path(self, project=None):
        if project is None:
            project = self.project
        return os.path.abspath(f"{project.upper()}.csv")

    def save_project_df(self, project, df):
        path = self.csv_path(project)
        df.to_csv(path, index=False)

    def get_csv_file(self, project_code):
        return os.path.join(self.project_dir, f"{project_code}.csv")

    def get_miv_data(self, project, filter_type=None, line_no=None, last_n=None):
        df = self.read_project_df(project)

        # بررسی وجود ستون‌های کلیدی
        if "Line No" not in df.columns or "Complete" not in df.columns:
            print("❌ ستون‌های ضروری در فایل موجود نیستند.")
            return pd.DataFrame()

        # نرمال‌سازی Line No برای مقایسه
        if line_no:
            norm_input = self.normalize_line_no(line_no)
            df = df[df["Line No"].apply(lambda x: self.normalize_line_no(x) == norm_input)]

        # فیلتر بر اساس ستون Complete
        if filter_type == "complete":
            df = df[df["Complete"].astype(str).str.lower() == "true"]
        elif filter_type == "incomplete":
            df = df[df["Complete"].astype(str).str.lower() != "true"]

        if last_n:
            df = df.tail(last_n)

        return df

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
        dfs = []

        if data_type == "miv":
            pattern = os.path.join(self.project_dir, "*.csv")
            exclude_keywords = ["MTO", "PROGRESS", "backup"]
        elif data_type == "mto":
            pattern = os.path.join(self.project_dir, "MTO-*.csv")
            exclude_keywords = []
        else:
            print("❌ نوع داده نامعتبر است. فقط 'miv' یا 'mto' مجاز است.")
            return pd.DataFrame()

        for file_path in glob.glob(pattern):
            filename = os.path.basename(file_path)
            if any(kw.lower() in filename.lower() for kw in exclude_keywords):
                continue
            try:
                df = pd.read_csv(file_path)
                if not df.empty:
                    dfs.append(df)
            except Exception as e:
                print(f"⚠️ خطا در خواندن {filename}: {e}")

        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    def read_all_miv_files(self):
        """
        خواندن تمام فایل‌های MIV به‌صورت ترکیب‌شده در یک DataFrame
        فقط فایل‌هایی که نه MTO هستند و نه PROGRESS
        """
        dfs = []
        pattern = os.path.join(self.project_dir, "*.csv")

        for file_path in glob.glob(pattern):
            filename = os.path.basename(file_path).lower()
            if "mto" in filename or "progress" in filename or "backup" in filename:
                continue

            try:
                df = pd.read_csv(file_path)
                if not df.empty:
                    df["__source_file__"] = os.path.basename(file_path)  # برای ردگیری منبع
                    dfs.append(df)
            except Exception as e:
                print(f"⚠️ خطا در خواندن فایل {filename}: {e}")

        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    def read_all_progress_files(self):
        """
        خواندن همه فایل‌های MTO_PROGRESS به صورت جداگانه
        خروجی: دیکشنری {project_name: DataFrame}
        """
        progress_data = {}
        pattern = os.path.join(self.project_dir, "MTO_PROGRESS-*.csv")

        for file_path in glob.glob(pattern):
            project_name = os.path.basename(file_path).replace("MTO_PROGRESS-", "").replace(".csv", "")
            try:
                df = pd.read_csv(file_path)
                progress_data[project_name] = df
            except Exception as e:
                print(f"⚠️ خطا در خواندن فایل پیشرفت {file_path}: {e}")

        return progress_data

    def normalize_line_no(self, line_no):
        return re.sub(r'[\s,\-\'\"]', '', str(line_no)).lower()

    def suggest_line_no(self, line_no_input):
        """
        با استفاده از difflib نزدیک‌ترین شماره خط موجود در فایل MTO رو پیشنهاد میده.
        """
        if self.mto_df.empty or "Line No" not in self.mto_df.columns:
            return None

        all_lines = self.mto_df["Line No"].dropna().unique().tolist()
        normalized_input = self.normalize_line_no(line_no_input)
        normalized_lines = {line: self.normalize_line_no(line) for line in all_lines}

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

    def get_used_qty(self, project, line_no, item_code, description):
        """
        مقدار مصرف‌شده از یک آیتم خاص را از فایل MTO_PROGRESS می‌خواند.
        ابتدا بر اساس Item Code جستجو می‌کند، در صورت نبودن Item Code یا خالی بودن آن، بر اساس Description جستجو می‌کند.
        """
        progress_file = os.path.join(self.project_dir, f"MTO_PROGRESS-{project}.csv")
        if not os.path.exists(progress_file):
            return 0

        try:
            df = pd.read_csv(progress_file)
            if not {"Line No", "Item Code", "Description", "Used Qty"}.issubset(df.columns):
                return 0

            # اول بر اساس Item Code جستجو می‌کنیم اگر item_code معتبر بود
            if item_code and str(item_code).strip():
                filtered = df[
                    (df["Line No"].astype(str) == str(line_no)) &
                    (df["Item Code"].astype(str).str.strip() == str(item_code).strip())
                    ]
            else:
                # در غیر این صورت بر اساس Description جستجو می‌کنیم
                filtered = df[
                    (df["Line No"].astype(str) == str(line_no)) &
                    (df["Description"].astype(str).str.strip() == str(description).strip())
                    ]

            if not filtered.empty:
                return pd.to_numeric(filtered["Used Qty"], errors="coerce").fillna(0).sum()

        except Exception as e:
            print(f"⚠️ خطا در خواندن فایل پیشرفت: {e}")

        return 0

    def update_progress_file(self, project, line_no, updates):
        """
        فایل پیشرفت پروژه را با استفاده از داده‌های جدید به‌روزرسانی می‌کند.
        برای آیتم‌هایی که Item Code ندارند، از Description به‌عنوان کلید استفاده می‌شود.
        برای محاسبه مقدار کل (Total Qty) از فایل MTO استفاده می‌شود:
            - اگر Type برابر با pipe باشد → مقدار از LENGTH(M)
            - در غیر این صورت → مقدار از QUANTITY
        """

        path = os.path.join(self.project_dir, f"MTO_PROGRESS-{project}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
        else:
            df = pd.DataFrame(columns=[
                "Line No", "Item Code", "Description", "Unit",
                "Total Qty", "Used Qty", "Remaining Qty", "Last Updated"
            ])

        mto_path = os.path.join(self.project_dir, f"MTO-{project}.csv")
        mto_df = pd.read_csv(mto_path) if os.path.exists(mto_path) else pd.DataFrame()

        for item_code, qty, unit, desc in updates:
            # اگر آیتم‌کد نامعتبر باشد، از Description استفاده می‌کنیم
            use_desc_key = not item_code or pd.isna(item_code) or str(item_code).strip() == ""

            # انتخاب ردیف MTO مرتبط با این خط و آیتم
            if use_desc_key:
                mto_match = mto_df[
                    (mto_df["Line No"].astype(str) == str(line_no)) &
                    (mto_df["Description"].astype(str).str.strip() == str(desc).strip())
                    ]
            else:
                mto_match = mto_df[
                    (mto_df["Line No"].astype(str) == str(line_no)) &
                    (mto_df["Itemcode"].astype(str).str.strip() == str(item_code).strip())
                    ]

            # محاسبه Total Qty با توجه به Type
            # محاسبه Total Qty با توجه به Type
            total_qty = 0
            if not mto_match.empty:
                mto_match = mto_match.copy()
                mto_match["Type"] = mto_match["Type"].astype(str).str.lower().str.replace(" ", "")

                pipe_mask = mto_match["Type"].str.contains("pipe", na=False)

                # اگر آیتم pipe باشد → LENGTH(M)
                if pipe_mask.any() and "LENGTH(M)" in mto_match.columns:
                    total_qty += pd.to_numeric(
                        mto_match.loc[pipe_mask, "LENGTH(M)"], errors='coerce'
                    ).fillna(0).sum()

                # اگر آیتم غیر pipe باشد → QUANTITY
                non_pipe_mask = ~pipe_mask
                if non_pipe_mask.any() and "QUANTITY" in mto_match.columns:
                    total_qty += pd.to_numeric(
                        mto_match.loc[non_pipe_mask, "QUANTITY"], errors='coerce'
                    ).fillna(0).sum()

            # ساختن شرط برای فیلتر رکوردهای موجود در فایل پیشرفت
            if use_desc_key:
                mask = (df["Line No"].astype(str) == str(line_no)) & \
                       (df["Description"].astype(str).str.strip() == str(desc).strip())
            else:
                mask = (df["Line No"].astype(str) == str(line_no)) & \
                       (df["Item Code"].astype(str).str.strip() == str(item_code).strip())

            # اگر رکورد موجود باشد → فقط آپدیت
            if not df[mask].empty:
                idx = df[mask].index[0]
                prev_used = pd.to_numeric(df.at[idx, "Used Qty"], errors='coerce') or 0
                new_used = prev_used + qty
                df.at[idx, "Used Qty"] = new_used
                df.at[idx, "Remaining Qty"] = max(0, total_qty - new_used)
                df.at[idx, "Last Updated"] = self.get_shamsi_date()
            else:
                # درج رکورد جدید
                df = pd.concat([df, pd.DataFrame([{
                    "Line No": line_no,
                    "Item Code": "" if use_desc_key else item_code,
                    "Description": desc,
                    "Unit": unit,
                    "Total Qty": total_qty,
                    "Used Qty": qty,
                    "Remaining Qty": max(0, total_qty - qty),
                    "Last Updated": self.get_shamsi_date()
                }])], ignore_index=True)

        df.to_csv(path, index=False)

    def is_line_miv_complete(self, line_no):
        progress_path = os.path.join(self.project_dir, f"MTO_PROGRESS-{self.project}.csv")
        mto_path = os.path.join(self.project_dir, f"MTO-{self.project}.csv")

        if not os.path.exists(progress_path) or not os.path.exists(mto_path):
            return False

        try:
            mto_df = pd.read_csv(mto_path)
            progress_df = pd.read_csv(progress_path)

            # تعریف تابع کمکی برای نرمال‌سازی کلیدها
            def normalize_key(value):
                if pd.isna(value):
                    return ""
                return str(value).strip().upper()

            # فیلتر کردن آیتم‌های MTO مربوط به خط مورد نظر
            mto_items = mto_df[mto_df["Line No"] == line_no].copy()

            if mto_items.empty:
                return False

            # ساخت کلیدهای نرمال‌شده برای آیتم‌ها
            mto_items["Key"] = mto_items.apply(
                lambda row: normalize_key(row["Itemcode"]) if normalize_key(row["Itemcode"]) != "" else normalize_key(
                    row["Description"]),
                axis=1
            )
            expected_items = mto_items["Key"].dropna().unique()

            # فیلتر کردن رکوردهای مصرفی مربوط به این خط
            used_items_df = progress_df[progress_df["Line No"] == line_no].copy()

            # ساخت کلیدهای نرمال‌شده برای رکوردهای مصرفی
            used_items_df["Key"] = used_items_df.apply(
                lambda row: normalize_key(row["Item Code"]) if normalize_key(row["Item Code"]) != "" else normalize_key(
                    row["Description"]),
                axis=1
            )

            # بررسی اینکه آیا تمام آیتم‌ها مصرف شده‌اند یا خیر
            for item_key in expected_items:
                row = used_items_df[used_items_df["Key"] == item_key]
                if row.empty:
                    return False  # هیچ رکوردی برای این آیتم ثبت نشده

                remaining = pd.to_numeric(row["Remaining Qty"], errors='coerce').fillna(1)
                if any(remaining > 0):
                    return False  # هنوز مقداری از این آیتم باقی مانده

            return True  # همه آیتم‌ها مصرف شده‌اند

        except Exception as e:
            print(f"⚠️ خطا در بررسی وضعیت کامل شدن خط: {e}")
            return False

    def get_project_progress(self):
        """

        پیشرفت کلی پروژه را با وزن‌دهی هر خط بر اساس مجموع مقدار موثر (LENGTH یا QUANTITY)
        ضرب در بیشترین قطر پایپ (P1BORE(IN)) آن خط محاسبه می‌کند.
        خروجی: دیکشنری شامل تعداد کل خطوط، مجموع وزن کل پروژه، وزن پیشرفت کرده، درصد پیشرفت.
        """
        import numpy as np

        mto_file = os.path.join(self.project_dir, f"MTO-{self.project}.csv")
        progress_file = os.path.join(self.project_dir, f"MTO_PROGRESS-{self.project}.csv")

        if not os.path.exists(mto_file):
            print(f"⚠️ فایل MTO برای پروژه {self.project} یافت نشد.")
            return {"total_lines": 0, "total_weight": 0, "done_weight": 0, "percentage": 0}

        try:
            mto_df = pd.read_csv(mto_file)
            if "Line No" not in mto_df.columns or mto_df["Line No"].empty:
                return {"total_lines": 0, "total_weight": 0, "done_weight": 0, "percentage": 0}

            if not os.path.exists(progress_file):
                print(f"⚠️ فایل پیشرفت برای پروژه {self.project} یافت نشد.")
                return {"total_lines": mto_df["Line No"].nunique(), "total_weight": 0, "done_weight": 0,
                        "percentage": 0}

            progress_df = pd.read_csv(progress_file)

            # نرمال سازی ستون‌ها برای مطمئن شدن از وجودشون
            if "Line No" not in progress_df.columns or "Used Qty" not in progress_df.columns:
                print(f"⚠️ ستون‌های ضروری در فایل پیشرفت موجود نیست.")
                return {"total_lines": mto_df["Line No"].nunique(), "total_weight": 0, "done_weight": 0,
                        "percentage": 0}

            total_weight = 0
            done_weight = 0

            # گروه‌بندی MTO بر اساس خط
            grouped = mto_df.groupby("Line No")

            for line_no, group in grouped:
                # بیشترین قطر پایپ در خط (P1BORE(IN))
                max_diameter = group["P1BORE(IN)"].replace("", np.nan).dropna().astype(float).max()
                if pd.isna(max_diameter):
                    max_diameter = 1  # اگر قطر نبود، وزن قطر رو 1 در نظر می‌گیریم (بی‌تاثیر)

                # مجموع مقدار موثر: اگر نوع پایپ (Type == "PIPE" یا کلاس پایپ) از LENGTH استفاده می‌کنیم، در غیر اینصورت QUANTITY
                # برای این مثال فرض می‌کنیم Type ستون "Type" دارد و مقدار پایپ "PIPE" است؛ ممکن است تغییر دهی بر اساس داده واقعی لازم باشد
                # ابتدا فیلتر پایپ‌ها:
                pipe_mask = group["Type"].str.upper() == "PIPE"
                length_sum = group.loc[pipe_mask, "LENGTH(M)"].replace("", 0).fillna(0).astype(float).sum()
                qty_sum = group.loc[~pipe_mask, "QUANTITY"].replace("", 0).fillna(0).astype(float).sum()

                qty_sum_effective = length_sum + qty_sum
                line_weight = qty_sum_effective * max_diameter
                total_weight += line_weight

                # محاسبه وزن انجام شده از روی فایل پیشرفت
                # برای هر ایتم در خط مربوطه در progress_df مجموع Used Qty را می‌گیریم
                progress_line_items = progress_df[progress_df["Line No"] == line_no]

                # مجموع وزن استفاده شده با اعمال قطر
                used_qty = 0
                for _, item_row in progress_line_items.iterrows():
                    desc = item_row["Description"]
                    used = item_row["Used Qty"]
                    # پیدا کردن سطرهای مچ در mto برای استخراج قطر همان ایتم
                    mto_items = group[group["Description"] == desc]
                    if not mto_items.empty:
                        item_max_dia = mto_items["P1BORE(IN)"].replace("", np.nan).dropna().astype(float).max()
                        if pd.isna(item_max_dia):
                            item_max_dia = max_diameter  # اگر قطر نبود از قطر خط استفاده می‌کنیم
                    else:
                        item_max_dia = max_diameter

                    used_qty += float(used) * item_max_dia

                done_weight += used_qty

            percentage = (done_weight / total_weight * 100) if total_weight > 0 else 0

            return {
                "total_lines": len(grouped),
                "total_weight": total_weight,
                "done_weight": done_weight,
                "percentage": round(percentage, 2)
            }

        except Exception as e:
            print(f"❌ خطا در محاسبه پیشرفت پروژه: {e}")
            return {"total_lines": 0, "total_weight": 0, "done_weight": 0, "percentage": 0}

    def get_line_progress(self, line_no):
        mto_path = os.path.join(self.project_dir, f"MTO-{self.project}.csv")
        progress_path = os.path.join(self.project_dir, f"MTO_PROGRESS-{self.project}.csv")

        default_return = {"total_qty": 0, "used_qty": 0, "percentage": 0}

        if not os.path.exists(mto_path):
            return default_return

        try:
            mto_df = pd.read_csv(mto_path)

            norm_line_no_input = str(line_no).strip().upper()
            mto_line = mto_df[mto_df["Line No"].astype(str).str.strip().str.upper() == norm_line_no_input].copy()

            if mto_line.empty:
                return default_return

            progress_line = pd.DataFrame()
            if os.path.exists(progress_path):
                progress_df = pd.read_csv(progress_path)
                progress_line = progress_df[
                    progress_df["Line No"].astype(str).str.strip().str.upper() == norm_line_no_input].copy()

            mto_line["Key"] = mto_line["Itemcode"].where(
                mto_line["Itemcode"].apply(lambda x: isinstance(x, str) and x.strip() != ""),
                mto_line["Description"]
            ).str.strip().str.upper()

            if not progress_line.empty:
                progress_line["Key"] = progress_line["Item Code"].where(
                    progress_line["Item Code"].apply(lambda x: isinstance(x, str) and x.strip() != ""),
                    progress_line["Description"]
                ).str.strip().str.upper()

            total_qty = 0
            used_qty = 0

            for _, mto_row in mto_line.iterrows():
                item_type = str(mto_row.get("Type", "")).strip().lower()

                # *** منطق اصلاح شده و نهایی برای محاسبه مقدار ***
                raw_val = 0
                if item_type == "pipe":
                    raw_val = mto_row.get("LENGTH(M)")
                else:
                    raw_val = mto_row.get("QUANTITY")

                # تبدیل مقدار به عدد و مدیریت مقادیر خالی یا غیرعددی
                numeric_val = pd.to_numeric(raw_val, errors='coerce')
                mto_item_total = 0 if pd.isna(numeric_val) else numeric_val

                total_qty += mto_item_total

                if not progress_line.empty:
                    key = mto_row["Key"]
                    match = progress_line[progress_line["Key"] == key]
                    if not match.empty:
                        used = pd.to_numeric(match["Used Qty"], errors='coerce').fillna(0).sum()
                        used_qty += min(used, mto_item_total)

            percentage = (used_qty / total_qty) * 100 if total_qty > 0 else 0

            return {
                "total_qty": round(total_qty, 2),
                "used_qty": round(used_qty, 2),
                "percentage": round(percentage, 2)
            }

        except Exception as e:
            print(f"⚠️ خطا در محاسبه پیشرفت خط '{line_no}': {e}")
            return default_return

    def get_line_material_breakdown(self, line_no):
        """
        Returns a dictionary of item codes and their actual quantities for a specific line.
        If item type is 'pipe', it uses LENGTH(M). Otherwise, it uses QUANTITY.
        Example:
            {
                "ITM-001": 120.0,
                "ITM-045": 40.0,
                "ITM-078": 25.0
            }
        """
        import os
        import pandas as pd

        mto_path = os.path.join(self.project_dir, f"MTO-{self.project}.csv")

        if not os.path.exists(mto_path):
            return {}

        try:
            mto_df = pd.read_csv(mto_path)

            # بررسی ستون‌های ضروری
            required_cols = {"Line No", "Itemcode", "Type"}
            if not required_cols.issubset(mto_df.columns):
                return {}

            filtered = mto_df[mto_df["Line No"].astype(str) == str(line_no)].copy()

            if filtered.empty:
                return {}

            # نرمال‌سازی فیلدها
            filtered["Itemcode"] = filtered["Itemcode"].astype(str).str.strip().str.upper()
            filtered["Type"] = filtered["Type"].astype(str).str.lower().str.replace(" ", "")

            # انتخاب ستون مناسب برای مقدار واقعی
            is_pipe = filtered["Type"].str.contains("pipe", na=False)

            filtered["ActualQty"] = 0.0  # مقدار جدید برای محاسبه نهایی

            if "LENGTH(M)" in filtered.columns:
                filtered.loc[is_pipe, "ActualQty"] = pd.to_numeric(
                    filtered.loc[is_pipe, "LENGTH(M)"], errors="coerce"
                ).fillna(0)

            if "QUANTITY" in filtered.columns:
                filtered.loc[~is_pipe, "ActualQty"] = pd.to_numeric(
                    filtered.loc[~is_pipe, "QUANTITY"], errors="coerce"
                ).fillna(0)

            # گروه‌بندی بر اساس Itemcode و جمع ActualQty
            breakdown = filtered.groupby("Itemcode")["ActualQty"].sum().to_dict()

            return breakdown

        except Exception as e:
            print(f"⚠️ Error reading material breakdown for line '{line_no}': {e}")
            return {}

    def get_line_material_progress(self, line_no):
        """
        برمی‌گرداند لیستی از دیکشنری‌ها شامل اطلاعات هر آیتم در خط داده‌شده.
        اطلاعات شامل: Item Code, Description, Total Qty, Used Qty, Remaining Qty, Unit

        [{
            "Item Code": "P1234",
            "Description": "Pipe 6in",
            "Total Qty": 12.0,
            "Used Qty": 8.0,
            "Remaining Qty": 4.0,
            "Unit": "M"
        }, ...]
        """
        mto_path = os.path.join(self.project_dir, f"MTO-{self.project}.csv")
        progress_path = os.path.join(self.project_dir, f"MTO_PROGRESS-{self.project}.csv")

        if not os.path.exists(mto_path):
            return []

        mto_df = pd.read_csv(mto_path)
        mto_df = mto_df[mto_df["Line No"].astype(str) == str(line_no)].copy()

        if mto_df.empty:
            return []

        # بارگذاری فایل پیشرفت در صورت وجود
        if os.path.exists(progress_path):
            progress_df = pd.read_csv(progress_path)
            progress_df = progress_df[progress_df["Line No"].astype(str) == str(line_no)].copy()
        else:
            progress_df = pd.DataFrame(columns=[
                "Line No", "Item Code", "Description", "Used Qty", "Remaining Qty", "Total Qty", "Unit"
            ])

        def normalize(value):
            return str(value).strip().upper() if not pd.isna(value) else ""

        # ساخت کلید تطبیق برای هر ردیف
        mto_df["Key"] = mto_df.apply(
            lambda row: normalize(row.get("Itemcode")) if normalize(row.get("Itemcode")) != "" else normalize(
                row.get("Description")),
            axis=1
        )

        if "Type" in mto_df.columns:
            mto_df["Type"] = mto_df["Type"].astype(str).str.lower().str.replace(" ", "")
        else:
            mto_df["Type"] = ""

        result = []
        for _, row in mto_df.iterrows():
            key = row["Key"]
            item_code = row.get("Itemcode", "")
            desc = row.get("Description", "")
            unit = row.get("Unit", "")
            type_ = row["Type"]

            if "pipe" in type_ and "LENGTH(M)" in row:
                total_qty = pd.to_numeric(row["LENGTH(M)"], errors='coerce')
            elif "QUANTITY" in row:
                total_qty = pd.to_numeric(row["QUANTITY"], errors='coerce')
            else:
                total_qty = 0

            progress_row = progress_df[
                progress_df.apply(lambda r: normalize(r["Item Code"]) if normalize(r["Item Code"]) != "" else normalize(
                    r["Description"]), axis=1) == key
                ]

            if not progress_row.empty:
                used_qty = pd.to_numeric(progress_row["Used Qty"].values[0], errors='coerce')
                remaining_qty = pd.to_numeric(progress_row["Remaining Qty"].values[0], errors='coerce')
            else:
                used_qty = 0
                remaining_qty = total_qty

            result.append({
                "Item Code": item_code,
                "Description": desc,
                "Unit": unit,
                "Total Qty": total_qty,
                "Used Qty": used_qty,
                "Remaining Qty": remaining_qty
            })

        return result

    def get_material_progress(self, project, line_no):
        progress_path = os.path.join(self.project_dir, f"MTO_PROGRESS-{project}.csv")
        mto_path = os.path.join(self.project_dir, f"MTO-{project}.csv")

        if not os.path.exists(progress_path) or not os.path.exists(mto_path):
            return pd.DataFrame()  # داده‌ای موجود نیست

        mto_df = pd.read_csv(mto_path)
        progress_df = pd.read_csv(progress_path)

        # پاکسازی نام ستون‌ها (مفید در برابر فاصله یا اشتباه تایپی)
        mto_df.columns = mto_df.columns.str.strip()
        progress_df.columns = progress_df.columns.str.strip()

        # فیلتر آیتم‌های مربوط به خط مورد نظر و ساخت کپی مستقل برای جلوگیری از هشدار
        mto_line = mto_df[mto_df["Line No"] == line_no].copy()
        progress_line = progress_df[progress_df["Line No"] == line_no].copy()

        # ساخت کلید یکتا برای تطبیق آیتم‌ها
        def normalize_key(row):
            if pd.notna(row.get("Itemcode")) and str(row["Itemcode"]).strip():
                return str(row["Itemcode"]).strip()
            else:
                return str(row.get("Description", "")).strip()

        mto_line["Key"] = mto_line.apply(normalize_key, axis=1)
        progress_line["Key"] = progress_line.apply(
            lambda row: str(row.get("Item Code", "")).strip() if str(row.get("Item Code", "")).strip()
            else str(row.get("Description", "")).strip(), axis=1)

        records = []
        keys = mto_line["Key"].unique()

        for key in keys:
            total_qty = mto_line[mto_line["Key"] == key]

            # بررسی نوع آیتم (pipe یا غیر pipe)
            pipe_mask = total_qty["Type"].astype(str).str.lower().str.replace(" ", "").str.contains("pipe", na=False)

            total_qty_value = 0
            if pipe_mask.any() and "LENGTH(M)" in total_qty.columns:
                total_qty_value += pd.to_numeric(total_qty.loc[pipe_mask, "LENGTH(M)"], errors='coerce').fillna(0).sum()
            if (~pipe_mask).any() and "QUANTITY" in total_qty.columns:
                total_qty_value += pd.to_numeric(total_qty.loc[~pipe_mask, "QUANTITY"], errors='coerce').fillna(0).sum()

            # مقدار مصرف‌شده
            used_qty_value = 0
            used_rows = progress_line[progress_line["Key"] == key]
            if not used_rows.empty and "Used Qty" in used_rows.columns:
                used_qty_value = pd.to_numeric(used_rows["Used Qty"], errors='coerce').fillna(0).sum()

            # گرفتن اطلاعات اولیه برای نمایش
            first_row = total_qty.iloc[0]
            records.append({
                "Item Code": first_row.get("Itemcode", ""),
                "Description": first_row.get("Description", ""),
                "Total Qty": total_qty_value,
                "Used Qty": used_qty_value,
                "Remaining Qty": max(0, total_qty_value - used_qty_value)
            })

        return pd.DataFrame(records)




