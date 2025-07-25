# 📦 Material-Issue-Tracker

نرم‌افزار دسکتاپی برای مدیریت، ثبت، پیگیری و خروجی گرفتن از **MIV (Material Issue Voucher)** در پروژه‌های صنعتی، با پشتیبانی از رابط گرافیکی، کنسول دستوری داخلی، فیلترهای پیشرفته و خروجی PDF/Excel.

---

## 🎯 قابلیت‌های کلیدی

- 📁 مدیریت چند پروژه‌ی مستقل
- 📝 ثبت و ویرایش رکوردهای MIV
- 🔍 جستجو بر اساس شماره خط یا MIV Tag
- 🧠 پیشنهاد خودکار شماره خط از فایل MTO
- 📤 خروجی PDF و Excel از رکوردها
- 🎛️ رابط گرافیکی با ظاهر دارک‌تم
- 🧮 مقایسه بین MIV و MTO
- 💬 کنسول دستوری داخلی (با autocomplete)
- 💾 سیستم بک‌آپ‌گیری پروژه‌ها
- 📋 نمایش لیست پروژه‌ها، خطوط، آیتم‌ها

---

## 🧩 ساختار پروژه

تمام کدها در یک فایل تجمیع‌شده به‌نام `ALL.py` قرار دارند، که ترکیبی از فایل‌های زیر است:

| بخش | توضیح |
|------|-------|
| `miv_registry.py` | کلاس اصلی برای مدیریت پروژه‌ها، رکوردها و CSV |
| `miv_gui.py` | رابط گرافیکی اصلی نرم‌افزار با tkinter |
| `console_text.py` | پیاده‌سازی کنسول داخلی نرم‌افزار |
| `editmiv.py` | پنجره ویرایش و حذف رکورد |
| `miv_table_viewer.py` | نمایش جدول با قابلیت فیلتر و خروجی |
| `MTO_Consumption_Window.py` | ثبت مصرف آیتم‌ها در هر خط |
| `line_no_autocomplete.py` | پیشنهاد شماره خط براساس فایل MTO |
| `helpwindow.py` | نمایش راهنمای دستورات داخلی |

---

## 🖥️ اجرای برنامه

```bash
python ALL.py

pip install pandas jdatetime openpyxl reportlab


register
show all MIV for P01
search tag XY123 in P02
compare mto and miv for 456789 in P01
check duplicates in P03
backup project P01

help
