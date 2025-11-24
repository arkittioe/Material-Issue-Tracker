# ui_components.py

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTextEdit, QStackedWidget, QDateEdit, QGridLayout, QWidget, QProgressBar
)
from PyQt6.QtCore import Qt, QDate, QStringListModel
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QCompleter

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class UIComponents:
    def __init__(self, main_window):
        self.main_window = main_window

    def create_registration_form(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.addWidget(QLabel("<h2>ثبت رکورد MIV جدید</h2>"))

        form_layout = QFormLayout()
        self.main_window.entries = {}

        # ردیف ویژه برای Line No با دکمه جستجوی فایل
        line_row_container = QWidget()
        line_row = QHBoxLayout(line_row_container)
        line_row.setContentsMargins(0, 0, 0, 0)

        self.main_window.entries["Line No"] = QLineEdit()
        self.main_window.entries["Line No"].setPlaceholderText(
            "شماره خط را وارد کنید (مثال: 10\"-P-210415-D6D-P).")

        self.main_window.iso_search_btn = QPushButton("🔎 جستجوی فایل‌های ISO/DWG")
        self.main_window.iso_search_btn.setToolTip(
            "جستجو در Y:\\Piping\\ISO بر اساس 6 رقم اولِ Line No (بدون توجه به علائم و حروف).")

        line_row.addWidget(self.main_window.entries["Line No"], 1)
        line_row.addWidget(self.main_window.iso_search_btn)

        form_layout.addRow("Line No:", line_row_container)

        # بقیه فیلدها
        for field in ["MIV Tag", "Location", "Status", "Registered For"]:
            self.main_window.entries[field] = QLineEdit()
            form_layout.addRow(f"{field}:", self.main_window.entries[field])

        self.main_window.line_completer_model = QStringListModel()

        # Completer برای فیلد ثبت
        self.main_window.register_completer = QCompleter(self.main_window.line_completer_model, self.main_window)
        self.main_window.register_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.main_window.register_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.main_window.entries["Line No"].setCompleter(self.main_window.register_completer)
        self.main_window.register_completer.popup().setMinimumSize(240, 160)

        self.main_window.register_btn = QPushButton("ثبت رکورد")
        layout.addLayout(form_layout)
        layout.addWidget(self.main_window.register_btn)
        layout.addStretch()

    def create_dashboard(self, parent_widget):
        layout = QVBoxLayout(parent_widget)

        # چیدمان افقی برای عنوان و دکمه به‌روزرسانی
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h3>Line Progress Dashboard</h3>"))
        header_layout.addStretch()
        self.main_window.update_dashboard_btn = QPushButton("🔄 Update Chart")
        header_layout.addWidget(self.main_window.update_dashboard_btn)
        layout.addLayout(header_layout)

        # نمودار پای‌چارت اصلی
        self.main_window.fig = Figure(figsize=(5, 4), dpi=100)
        self.main_window.canvas = FigureCanvas(self.main_window.fig)
        layout.addWidget(self.main_window.canvas)
        self.main_window.dashboard_ax = self.main_window.fig.add_subplot(111)
        self.main_window.dashboard_ax.text(0.5, 0.5, "Enter a line number", ha='center', va='center')
        self.main_window.canvas.draw()

        # دکمه‌های زیر نمودار
        details_button_layout = QHBoxLayout()

        self.main_window.details_btn = QPushButton("Show Project Details")
        details_button_layout.addWidget(self.main_window.details_btn)

        self.main_window.export_line_status_btn = QPushButton("📄 Export Line Status")
        self.main_window.export_line_status_btn.setStyleSheet("background-color: #007bff; color: white;")
        details_button_layout.addWidget(self.main_window.export_line_status_btn)

        layout.addLayout(details_button_layout)

    def create_search_box(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.addWidget(QLabel("<h3>جستجو و نمایش پیشرفته</h3>"))

        # ردیف اول: نوع جستجو
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("نوع جستجو:"))
        self.main_window.search_type_combo = QComboBox()
        self.main_window.search_type_combo.addItems([
            "Line Number",
            "MIV Tag",
            "Registered For",
            "Registered By",
            "Date Range",
            "Completion Status"
        ])
        self.main_window.search_type_combo.setCurrentIndex(0)
        self.main_window.search_type_combo.currentTextChanged.connect(self._update_search_widgets)
        type_layout.addWidget(self.main_window.search_type_combo, 1)
        layout.addLayout(type_layout)

        # کانتینر برای ویجت‌های جستجو
        self.main_window.search_widgets_stack = QStackedWidget()

        # صفحه 1: Line Number
        line_page = QWidget()
        line_layout = QHBoxLayout(line_page)
        line_layout.setContentsMargins(0, 0, 0, 0)
        self.main_window.search_entry_line = QLineEdit()
        self.main_window.search_entry_line.setPlaceholderText('مثال: 10"-P-210415-D6D-P')
        line_layout.addWidget(self.main_window.search_entry_line)
        self.main_window.search_widgets_stack.addWidget(line_page)

        # Completer برای Line Number
        self.main_window.search_completer = QCompleter(self.main_window.line_completer_model, self.main_window)
        self.main_window.search_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.main_window.search_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.main_window.search_entry_line.setCompleter(self.main_window.search_completer)
        self.main_window.search_completer.popup().setMinimumSize(240, 160)

        # صفحه 2: MIV Tag
        tag_page = QWidget()
        tag_layout = QHBoxLayout(tag_page)
        tag_layout.setContentsMargins(0, 0, 0, 0)
        self.main_window.search_entry_tag = QLineEdit()
        self.main_window.search_entry_tag.setPlaceholderText("مثال: MIV123456 یا 123456")
        tag_layout.addWidget(self.main_window.search_entry_tag)
        self.main_window.search_widgets_stack.addWidget(tag_page)

        # صفحه 3: Registered For
        reg_for_page = QWidget()
        reg_for_layout = QHBoxLayout(reg_for_page)
        reg_for_layout.setContentsMargins(0, 0, 0, 0)
        self.main_window.search_entry_reg_for = QLineEdit()
        self.main_window.search_entry_reg_for.setPlaceholderText("مثال: علی رضایی")
        reg_for_layout.addWidget(self.main_window.search_entry_reg_for)
        self.main_window.search_widgets_stack.addWidget(reg_for_page)

        # صفحه 4: Registered By
        reg_by_page = QWidget()
        reg_by_layout = QHBoxLayout(reg_by_page)
        reg_by_layout.setContentsMargins(0, 0, 0, 0)
        self.main_window.search_entry_reg_by = QLineEdit()
        self.main_window.search_entry_reg_by.setPlaceholderText("مثال: hizadi")
        reg_by_layout.addWidget(self.main_window.search_entry_reg_by)
        self.main_window.search_widgets_stack.addWidget(reg_by_page)

        # صفحه 5: Date Range
        date_page = QWidget()
        date_layout = QGridLayout(date_page)
        date_layout.setContentsMargins(0, 0, 0, 0)

        date_layout.addWidget(QLabel("از تاریخ:"), 0, 0)
        self.main_window.search_date_start = QDateEdit()
        self.main_window.search_date_start.setCalendarPopup(True)
        self.main_window.search_date_start.setDate(QDate.currentDate().addMonths(-1))
        self.main_window.search_date_start.setDisplayFormat("yyyy/MM/dd")
        date_layout.addWidget(self.main_window.search_date_start, 0, 1)

        date_layout.addWidget(QLabel("تا تاریخ:"), 1, 0)
        self.main_window.search_date_end = QDateEdit()
        self.main_window.search_date_end.setCalendarPopup(True)
        self.main_window.search_date_end.setDate(QDate.currentDate())
        self.main_window.search_date_end.setDisplayFormat("yyyy/MM/dd")
        date_layout.addWidget(self.main_window.search_date_end, 1, 1)

        date_layout.addWidget(QLabel("وضعیت:"), 2, 0)
        self.main_window.search_date_status = QComboBox()
        self.main_window.search_date_status.addItems(["همه", "تکمیل شده", "تکمیل نشده"])
        date_layout.addWidget(self.main_window.search_date_status, 2, 1)

        self.main_window.search_widgets_stack.addWidget(date_page)

        # صفحه 6: Completion Status
        status_page = QWidget()
        status_layout = QHBoxLayout(status_page)
        status_layout.setContentsMargins(0, 0, 0, 0)
        self.main_window.search_completion_combo = QComboBox()
        self.main_window.search_completion_combo.addItems(["تکمیل شده", "تکمیل نشده"])
        status_layout.addWidget(self.main_window.search_completion_combo)
        self.main_window.search_widgets_stack.addWidget(status_page)

        layout.addWidget(self.main_window.search_widgets_stack)

        # دکمه جستجو
        self.main_window.search_btn = QPushButton("🔍 جستجو")
        self.main_window.search_btn.setStyleSheet("font-size: 14px; padding: 8px;")
        layout.addWidget(self.main_window.search_btn)

    def _update_search_widgets(self, search_type: str):
        type_index_map = {
            "Line Number": 0,
            "MIV Tag": 1,
            "Registered For": 2,
            "Registered By": 3,
            "Date Range": 4,
            "Completion Status": 5
        }
        index = type_index_map.get(search_type, 0)
        self.main_window.search_widgets_stack.setCurrentIndex(index)

    def create_console(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        self.main_window.project_combo = QComboBox()
        self.main_window.load_project_btn = QPushButton("بارگذاری پروژه")

        project_layout = QHBoxLayout()
        project_layout.addWidget(QLabel("پروژه فعال:"))
        project_layout.addWidget(self.main_window.project_combo, 1)
        project_layout.addWidget(self.main_window.load_project_btn)

        layout.addLayout(project_layout)

        # لیبل وضعیت ISO
        self.main_window.iso_status_label = QLabel("وضعیت ایندکس ISO: در حال بررسی...")
        self.main_window.iso_status_label.setStyleSheet("padding: 4px; color: #f1fa8c;")

        # دکمه‌های مدیریت
        management_layout = QHBoxLayout()
        self.main_window.manage_spool_btn = QPushButton("مدیریت اسپول‌ها")
        self.main_window.update_data_btn = QPushButton("🔄 به‌روزرسانی از CSV")
        self.main_window.update_data_btn.setStyleSheet("background-color: #6272a4;")

        # QProgressBar
        self.main_window.iso_progress_bar = QProgressBar()
        self.main_window.iso_progress_bar.setRange(0, 100)
        self.main_window.iso_progress_bar.setValue(0)
        self.main_window.iso_progress_bar.setTextVisible(True)
        self.main_window.iso_progress_bar.setFormat("ایندکس ISO: %p%")
        self.main_window.iso_progress_bar.hide()

        self.main_window.console_output = QTextEdit()
        self.main_window.console_output.setReadOnly(True)
        self.main_window.console_output.setFont(QFont("Consolas", 11))
        self.main_window.console_output.setStyleSheet("background-color: #2b2b2b; color: #f8f8f2;")

        layout.addWidget(self.main_window.console_output, 1)
        management_layout.addWidget(self.main_window.manage_spool_btn)
        management_layout.addWidget(self.main_window.update_data_btn)
        layout.addLayout(management_layout)
        layout.addWidget(self.main_window.iso_progress_bar)
