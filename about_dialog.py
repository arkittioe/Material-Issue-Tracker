# file: about_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QTextEdit, QFrame
)
from PyQt6.QtGui import QPixmap, QFont, QDesktopServices
from PyQt6.QtCore import Qt, QUrl
import sys
import platform


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    import os
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About MIV Manager")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # ═══════════════════════════════════════════
        # بخش هدر با لوگو و عنوان
        # ═══════════════════════════════════════════
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2c3e50, stop:1 #34495e
                );
                border-radius: 10px;
                padding: 20px;
            }
        """)

        header_layout = QHBoxLayout(header_frame)

        # لوگو (آیکون برنامه)
        logo_label = QLabel()
        icon_pixmap = QPixmap(resource_path("IC.ico"))
        if not icon_pixmap.isNull():
            logo_label.setPixmap(icon_pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio))
        else:
            logo_label.setText("📊")
            logo_label.setStyleSheet("font-size: 60px;")

        # اطلاعات اصلی
        info_layout = QVBoxLayout()

        title_label = QLabel("MIV Manager")
        title_label.setStyleSheet("color: white; font-size: 28px; font-weight: bold;")

        subtitle_label = QLabel("Material Issue Tracker & Inventory Management System")
        subtitle_label.setStyleSheet("color: #ecf0f1; font-size: 12px;")
        subtitle_label.setWordWrap(True)

        version_label = QLabel("Version 2.0.0 | Build 2025.11.25")
        version_label.setStyleSheet("color: #95a5a6; font-size: 10px; margin-top: 10px;")

        info_layout.addWidget(title_label)
        info_layout.addWidget(subtitle_label)
        info_layout.addWidget(version_label)
        info_layout.addStretch()

        header_layout.addWidget(logo_label)
        header_layout.addLayout(info_layout)

        layout.addWidget(header_frame)

        # ═══════════════════════════════════════════
        # تب‌ها
        # ═══════════════════════════════════════════
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
            }
            QTabBar::tab {
                padding: 8px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
            }
        """)

        # تب 1: About
        about_tab = self._create_about_tab()
        tabs.addTab(about_tab, "📖 About")

        # تب 2: Features
        features_tab = self._create_features_tab()
        tabs.addTab(features_tab, "✨ Features")

        # تب 3: Credits
        credits_tab = self._create_credits_tab()
        tabs.addTab(credits_tab, "👥 Credits")

        # تب 4: System Info
        system_tab = self._create_system_tab()
        tabs.addTab(system_tab, "💻 System")

        layout.addWidget(tabs)

        # ═══════════════════════════════════════════
        # دکمه‌های پایین
        # ═══════════════════════════════════════════
        buttons_layout = QHBoxLayout()

        github_btn = QPushButton("🐙 GitHub Repository")
        github_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        github_btn.clicked.connect(self._open_github)

        email_btn = QPushButton("📧 Contact Developer")
        email_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        email_btn.clicked.connect(self._send_email)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        close_btn.clicked.connect(self.accept)

        buttons_layout.addWidget(github_btn)
        buttons_layout.addWidget(email_btn)
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

    def _create_about_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
        <div style='font-family: Arial; line-height: 1.6;'>
            <h3 style='color: #2c3e50;'>📋 درباره برنامه</h3>
            <p>
                <b>MIV Manager</b> یک سیستم جامع برای مدیریت و پیگیری متریال در پروژه‌های صنعتی است.
                این برنامه به شما امکان می‌دهد:
            </p>
            <ul>
                <li>ثبت و پیگیری Material Issue Voucher (MIV)</li>
                <li>مدیریت Material Take-Off (MTO)</li>
                <li>کنترل موجودی انبار اسپول (Spool Inventory)</li>
                <li>تولید گزارش‌های جامع و تحلیلی</li>
                <li>نمایش داشبورد پیشرفت پروژه به صورت Real-time</li>
            </ul>

            <h3 style='color: #2c3e50; margin-top: 20px;'>🎯 هدف</h3>
            <p>
                کاهش خطاهای انسانی، افزایش سرعت ثبت اطلاعات، و بهبود شفافیت در فرآیندهای 
                صدور متریال برای پروژه‌های EPC.
            </p>

            <h3 style='color: #2c3e50; margin-top: 20px;'>📜 License</h3>
            <p>
                این نرم‌افزار تحت مجوز MIT منتشر شده است. برای اطلاعات بیشتر به 
                <a href='https://github.com/arkittioe/Material-Issue-Tracker-SQLDB'>مخزن GitHub</a> مراجعه کنید.
            </p>
        </div>
        """)
        text.setStyleSheet("background-color: #ecf0f1; border: none; padding: 10px;")

        layout.addWidget(text)
        return widget

    def _create_features_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
        <div style='font-family: Arial;'>
            <h3 style='color: #16a085;'>🚀 قابلیت‌های اصلی</h3>

            <h4 style='color: #2c3e50;'>📝 مدیریت MIV</h4>
            <ul>
                <li>ثبت سریع رکورد MIV با Autocomplete هوشمند</li>
                <li>جستجوی پیشرفته با فیلترهای متنوع</li>
                <li>ویرایش و حذف رکوردها با امنیت کامل</li>
                <li>پیگیری تاریخچه تغییرات</li>
            </ul>

            <h4 style='color: #2c3e50;'>📊 گزارش‌گیری</h4>
            <ul>
                <li>گزارش خلاصه MTO (MTO Summary Report)</li>
                <li>گزارش وضعیت خطوط (Line Status List)</li>
                <li>گزارش کسری متریال (Shortage Report)</li>
                <li>گزارش موجودی اسپول (Spool Inventory)</li>
                <li>خروجی Excel و PDF با فرمت حرفه‌ای</li>
            </ul>

            <h4 style='color: #2c3e50;'>🎨 داشبورد تحلیلی</h4>
            <ul>
                <li>نمودارهای تعاملی Pie Chart و Bar Chart</li>
                <li>محاسبه خودکار درصد پیشرفت (به واحد inch-dia)</li>
                <li>نمایش Real-time اطلاعات</li>
            </ul>

            <h4 style='color: #2c3e50;'>🔍 جستجوی ISO</h4>
            <ul>
                <li>ایندکس خودکار فایل‌های ISO و DWG</li>
                <li>جستجوی سریع بر اساس 6 رقم Line Number</li>
                <li>نمایش مستقیم فایل‌ها</li>
            </ul>

            <h4 style='color: #2c3e50;'>🗄️ مدیریت اسپول</h4>
            <ul>
                <li>ثبت اسپول‌های جدید</li>
                <li>مدیریت موجودی</li>
                <li>پیگیری تاریخچه مصرف</li>
            </ul>
        </div>
        """)
        text.setStyleSheet("background-color: #ecf0f1; border: none; padding: 10px;")

        layout.addWidget(text)
        return widget

    def _create_credits_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
        <div style='font-family: Arial; line-height: 1.8;'>
            <h3 style='color: #8e44ad;'>👨‍💻 توسعه‌دهنده</h3>
            <p style='font-size: 14px;'>
                <b>Hossein Izadi</b><br>
                Industrial Engineer & Python Developer<br>
                📧 Email: <a href='mailto:arkittoe@gmail.com'>arkittoe@gmail.com</a><br>
                🐙 GitHub: <a href='https://github.com/arkittioe'>@arkittioe</a>
            </p>

            <h3 style='color: #8e44ad; margin-top: 30px;'>🛠️ تکنولوژی‌های استفاده شده</h3>
            <table style='width: 100%; border-collapse: collapse;'>
                <tr>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'><b>Backend</b></td>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'>Python 3.11+</td>
                </tr>
                <tr>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'><b>GUI Framework</b></td>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'>PyQt6</td>
                </tr>
                <tr>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'><b>Database</b></td>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'>PostgreSQL + SQLAlchemy ORM</td>
                </tr>
                <tr>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'><b>Data Processing</b></td>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'>Pandas, NumPy</td>
                </tr>
                <tr>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'><b>Visualization</b></td>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'>Matplotlib</td>
                </tr>
                <tr>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'><b>Reporting</b></td>
                    <td style='padding: 8px; border-bottom: 1px solid #bdc3c7;'>ReportLab, Openpyxl</td>
                </tr>
                <tr>
                    <td style='padding: 8px;'><b>File Monitoring</b></td>
                    <td style='padding: 8px;'>Watchdog</td>
                </tr>
            </table>

            <h3 style='color: #8e44ad; margin-top: 30px;'>🙏 تشکر ویژه</h3>
            <p>
                از تمام سازندگان کتابخانه‌های Open Source که این پروژه را ممکن ساختند،
                کمال تشکر را داریم.
            </p>
        </div>
        """)
        text.setStyleSheet("background-color: #ecf0f1; border: none; padding: 10px;")

        layout.addWidget(text)
        return widget

    def _create_system_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # دریافت اطلاعات سیستم
        system_info = f"""
        <div style='font-family: Consolas, monospace; font-size: 12px;'>
            <h3 style='color: #e74c3c;'>💻 System Information</h3>
            <table style='width: 100%;'>
                <tr>
                    <td style='padding: 5px;'><b>Operating System:</b></td>
                    <td style='padding: 5px;'>{platform.system()} {platform.release()}</td>
                </tr>
                <tr>
                    <td style='padding: 5px;'><b>Platform:</b></td>
                    <td style='padding: 5px;'>{platform.platform()}</td>
                </tr>
                <tr>
                    <td style='padding: 5px;'><b>Machine:</b></td>
                    <td style='padding: 5px;'>{platform.machine()}</td>
                </tr>
                <tr>
                    <td style='padding: 5px;'><b>Processor:</b></td>
                    <td style='padding: 5px;'>{platform.processor() or 'N/A'}</td>
                </tr>
                <tr>
                    <td style='padding: 5px;'><b>Python Version:</b></td>
                    <td style='padding: 5px;'>{platform.python_version()}</td>
                </tr>
                <tr>
                    <td style='padding: 5px;'><b>PyQt6 Version:</b></td>
                    <td style='padding: 5px;'>{self._get_pyqt_version()}</td>
                </tr>
            </table>

            <h3 style='color: #e74c3c; margin-top: 20px;'>🔧 Application Paths</h3>
            <table style='width: 100%;'>
                <tr>
                    <td style='padding: 5px;'><b>Executable:</b></td>
                    <td style='padding: 5px; word-break: break-all;'>{sys.executable}</td>
                </tr>
                <tr>
                    <td style='padding: 5px;'><b>Working Directory:</b></td>
                    <td style='padding: 5px; word-break: break-all;'>{sys.path[0]}</td>
                </tr>
            </table>
        </div>
        """

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml(system_info)
        text.setStyleSheet("background-color: #ecf0f1; border: none; padding: 10px;")

        layout.addWidget(text)
        return widget

    def _get_pyqt_version(self):
        try:
            from PyQt6.QtCore import PYQT_VERSION_STR
            return PYQT_VERSION_STR
        except:
            return "Unknown"

    def _open_github(self):
        QDesktopServices.openUrl(
            QUrl("https://github.com/arkittioe/Material-Issue-Tracker-SQLDB")
        )

    def _send_email(self):
        QDesktopServices.openUrl(
            QUrl("mailto:arkittoe@gmail.com?subject=MIV Manager Feedback")
        )


class HelpDialog(QDialog):
    """دیالوگ راهنمای استفاده با Keyboard Shortcuts"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help - User Guide")
        self.setMinimumSize(700, 600)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # تب‌های راهنما
        tabs = QTabWidget()

        # تب 1: Quick Start
        quick_start_tab = self._create_quick_start_tab()
        tabs.addTab(quick_start_tab, "🚀 Quick Start")

        # تب 2: Keyboard Shortcuts
        shortcuts_tab = self._create_shortcuts_tab()
        tabs.addTab(shortcuts_tab, "⌨️ Shortcuts")

        # تب 3: FAQ
        faq_tab = self._create_faq_tab()
        tabs.addTab(faq_tab, "❓ FAQ")

        layout.addWidget(tabs)

        # دکمه بستن
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _create_quick_start_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
        <div style='font-family: Arial;'>
            <h2 style='color: #27ae60;'>🚀 راهنمای سریع شروع</h2>

            <h3>گام 1️⃣: انتخاب پروژه</h3>
            <ol>
                <li>از لیست کشویی "پروژه فعال" پروژه مورد نظر را انتخاب کنید</li>
                <li>روی دکمه "بارگذاری پروژه" کلیک کنید</li>
            </ol>

            <h3>گام 2️⃣: ثبت رکورد MIV</h3>
            <ol>
                <li>در بخش "ثبت رکورد MIV جدید"، شماره خط را وارد کنید</li>
                <li>از پیشنهادهای خودکار (Autocomplete) استفاده کنید</li>
                <li>سایر فیلدها را پر کنید</li>
                <li>روی "ثبت رکورد" کلیک کنید</li>
            </ol>

            <h3>گام 3️⃣: مشاهده داشبورد</h3>
            <ol>
                <li>شماره خط را وارد کنید</li>
                <li>روی "🔄 Update Chart" کلیک کنید</li>
                <li>برای جزئیات بیشتر، روی "Show Project Details" کلیک کنید</li>
            </ol>

            <h3>گام 4️⃣: جستجو</h3>
            <ol>
                <li>نوع جستجو را انتخاب کنید (Line Number, MIV Tag, ...)</li>
                <li>مقدار مورد نظر را وارد کنید</li>
                <li>روی "🔍 جستجو" کلیک کنید</li>
            </ol>

            <h3>گام 5️⃣: خروجی گرفتن</h3>
            <ol>
                <li>از منوی "Reports" گزینه مورد نظر را انتخاب کنید</li>
                <li>محل ذخیره فایل را مشخص کنید</li>
                <li>فرمت (Excel یا PDF) را انتخاب کنید</li>
            </ol>
        </div>
        """)
        text.setStyleSheet("background-color: #ecf0f1; border: none; padding: 10px;")

        layout.addWidget(text)
        return widget

    def _create_shortcuts_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
        <div style='font-family: Arial;'>
            <h2 style='color: #3498db;'>⌨️ میانبرهای صفحه‌کلید</h2>

            <table style='width: 100%; border-collapse: collapse;'>
                <thead>
                    <tr style='background-color: #34495e; color: white;'>
                        <th style='padding: 10px; text-align: left;'>Action</th>
                        <th style='padding: 10px; text-align: left;'>Shortcut</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style='background-color: #ecf0f1;'>
                        <td style='padding: 8px;'>ثبت رکورد جدید</td>
                        <td style='padding: 8px;'><kbd>Ctrl + N</kbd></td>
                    </tr>
                    <tr>
                        <td style='padding: 8px;'>جستجو</td>
                        <td style='padding: 8px;'><kbd>Ctrl + F</kbd></td>
                    </tr>
                    <tr style='background-color: #ecf0f1;'>
                        <td style='padding: 8px;'>به‌روزرسانی نمودار</td>
                        <td style='padding: 8px;'><kbd>F5</kbd></td>
                    </tr>
                    <tr>
                        <td style='padding: 8px;'>خروجی Excel</td>
                        <td style='padding: 8px;'><kbd>Ctrl + E</kbd></td>
                    </tr>
                    <tr style='background-color: #ecf0f1;'>
                        <td style='padding: 8px;'>باز کردن راهنما</td>
                        <td style='padding: 8px;'><kbd>F1</kbd></td>
                    </tr>
                    <tr>
                        <td style='padding: 8px;'>بستن برنامه</td>
                        <td style='padding: 8px;'><kbd>Alt + F4</kbd></td>
                    </tr>
                </tbody>
            </table>

            <h3 style='margin-top: 30px;'>نکات کاربردی:</h3>
            <ul>
                <li>در فیلد "Line No" از <kbd>↑</kbd> و <kbd>↓</kbd> برای انتخاب از پیشنهادها استفاده کنید</li>
                <li>در جستجو، <kbd>Enter</kbd> برای جستجوی سریع</li>
                <li>در جداول، <kbd>Ctrl + C</kbd> برای کپی ردیف انتخابی</li>
            </ul>
        </div>
        """)
        text.setStyleSheet("background-color: #ecf0f1; border: none; padding: 10px;")

        layout.addWidget(text)
        return widget

    def _create_faq_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
        <div style='font-family: Arial;'>
            <h2 style='color: #e67e22;'>❓ سوالات متداول (FAQ)</h2>

            <h3 style='color: #2c3e50;'>❓ چگونه یک پروژه جدید اضافه کنم؟</h3>
            <p>
                هنگام آپدیت فایل CSV، اگر پروژه جدیدی باشد به صورت خودکار ساخته می‌شود.
                فقط کافیست نام فایل به فرمت <code>MTO-ProjectName.csv</code> باشد.
            </p>

            <h3 style='color: #2c3e50;'>❓ چرا نمودار پیشرفت نمایش داده نمی‌شود؟</h3>
            <p>
                دلایل احتمالی:<br>
                ✔️ ابتدا یک پروژه را بارگذاری کنید<br>
                ✔️ شماره خط را صحیح وارد کنید<br>
                ✔️ حتماً روی دکمه "🔄 Update Chart" کلیک کنید
            </p>

            <h3 style='color: #2c3e50;'>❓ چگونه فایل‌های ISO را جستجو کنم؟</h3>
            <p>
                با کلیک روی دکمه "🔎 جستجوی فایل‌های ISO/DWG" در کنار فیلد Line No،
                برنامه به صورت خودکار فایل‌های مرتبط را پیدا می‌کند.
            </p>

            <h3 style='color: #2c3e50;'>❓ فرمت فایل خروجی چیست؟</h3>
            <p>
                گزارش‌ها به دو فرمت قابل خروجی هستند:<br>
                📊 <b>Excel (.xlsx)</b> - برای ویرایش و تحلیل بیشتر<br>
                📄 <b>PDF (.pdf)</b> - برای پرینت و آرشیو
            </p>

            <h3 style='color: #2c3e50;'>❓ خطای "Connection Failed" چه معنایی دارد؟</h3>
            <p>
                این خطا به معنای عدم اتصال به دیتابیس PostgreSQL است.<br>
                ✔️ از دسترسی به سرور (192.168.2.55:5432) اطمینان حاصل کنید<br>
                ✔️ نام کاربری و رمز عبور را بررسی کنید<br>
                ✔️ اتصال شبکه خود را چک کنید
            </p>

            <h3 style='color: #2c3e50;'>❓ چگونه داده‌ها را پشتیبان بگیرم؟</h3>
            <p>
                از منوی "Reports" گزارش‌های مورد نظر را خروجی بگیرید.
                همچنین از بخش "Spool Manager" امکان خروجی کامل موجودی اسپول وجود دارد.
            </p>
        </div>
        """)
        text.setStyleSheet("background-color: #ecf0f1; border: none; padding: 10px;")

        layout.addWidget(text)
        return widget
