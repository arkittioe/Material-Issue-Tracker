# file: advanced_dashboard_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QProgressBar, QFrame, QSizePolicy,
    QMessageBox, QFileDialog, QScrollArea, QDateEdit
)
from PyQt6.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal, QDate

from PyQt6.QtGui import QFont, QColor, QPalette

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from typing import Dict, List, Any
import logging


class DataLoadWorker(QThread):
    """Thread جداگانه برای بارگذاری داده‌ها"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, dm, project_id):
        super().__init__()
        self.dm = dm
        self.project_id = project_id

    def run(self):
        try:
            data = {
                'project_progress': self.dm.get_project_progress(self.project_id),
                'lines_data': self._load_lines_fast(),
                'mto_summary': self.dm.get_project_mto_summary(self.project_id),
                'shortage_data': self.dm.get_shortage_report(self.project_id)
            }
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

    def _load_lines_fast(self):
        """بارگذاری سریع خطوط با کوئری بهینه"""
        lines_data = []

        # ✅ پاک کردن cache
        if hasattr(self.dm.get_line_progress, 'cache_clear'):
            self.dm.get_line_progress.cache_clear()

        session = self.dm.get_session()
        try:
            from models import MTOItem, MIVRecord
            from sqlalchemy import func

            # ✅ یک کوئری برای همه (بهینه)
            results = session.query(
                MTOItem.line_no,
                func.max(MIVRecord.last_updated).label('last_activity')
            ).outerjoin(
                MIVRecord,
                (MIVRecord.project_id == self.project_id) &
                (MIVRecord.line_no == MTOItem.line_no)
            ).filter(
                MTOItem.project_id == self.project_id
            ).group_by(MTOItem.line_no).all()

            for line_no, last_activity in results:
                progress_info = self.dm.get_line_progress(
                    self.project_id,
                    line_no,
                    readonly=False
                )

                lines_data.append({
                    "Line No": line_no,
                    "Progress (%)": round(progress_info.get("percentage", 0), 2),
                    "Total (inch-dia)": round(progress_info.get("total_weight", 0), 2),
                    "Used (inch-dia)": round(progress_info.get("done_weight", 0), 2),
                    "Status": "Complete" if progress_info.get("percentage", 0) >= 99.9 else "In-Progress",
                    "Last Activity Date": last_activity.strftime('%Y-%m-%d') if last_activity else "N/A"
                })

            lines_data.sort(key=lambda x: x["Progress (%)"], reverse=True)
            return lines_data

        finally:
            session.close()


class AdvancedDashboardDialog(QDialog):
    """
    داشبورد پیشرفته پروژه با 4 تب اصلی:
    - Tab 1: Project Overview (KPI Cards + Charts)
    - Tab 2: Lines Status (جدول با Progress Bar)
    - Tab 3: Material Analysis (MTO Summary + Shortage)
    - Tab 4: Activity Timeline (آخرین فعالیت‌ها)
    """

    def __init__(self, data_manager, project_id: int, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.project_id = project_id

        # دریافت اطلاعات پروژه
        session = self.dm.get_session()
        try:
            from models import Project
            self.project = session.get(Project, project_id)
            if not self.project:
                raise ValueError(f"Project with ID {project_id} not found.")
        finally:
            session.close()

        self.setWindowTitle(f"📊 Advanced Dashboard - {self.project.name}")
        self.setMinimumSize(1400, 900)

        # داده‌های اصلی که یکبار لود می‌شن
        self.project_progress = {}
        self.lines_data = []
        self.mto_summary = {}
        self.shortage_data = {}

        self.setup_ui()
        self.load_all_data()

    def setup_ui(self):
        """ساخت رابط کاربری اصلی"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # عنوان اصلی
        title_label = QLabel(f"🏗️ Project: {self.project.name}")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Tab Widget اصلی
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Arial", 10))

        # ساخت تب‌ها
        self.tab_overview = self.create_overview_tab()
        self.tab_lines = self.create_lines_tab()
        self.tab_materials = self.create_materials_tab()
        self.tab_timeline = self.create_timeline_tab()

        self.tab_widget.addTab(self.tab_overview, "📊 Overview")
        self.tab_widget.addTab(self.tab_lines, "📋 Lines Status")
        self.tab_widget.addTab(self.tab_materials, "🔧 Material Analysis")
        self.tab_widget.addTab(self.tab_timeline, "📅 Activity Timeline")

        main_layout.addWidget(self.tab_widget)

        # دکمه‌های پایینی
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh All")
        refresh_btn.setFont(QFont("Arial", 10))
        refresh_btn.clicked.connect(self.load_all_data)
        buttons_layout.addWidget(refresh_btn)

        close_btn = QPushButton("✖ Close")
        close_btn.setFont(QFont("Arial", 10))
        close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(close_btn)

        main_layout.addLayout(buttons_layout)

    # ========================================================================
    # TAB 1: PROJECT OVERVIEW
    # ========================================================================

    def create_overview_tab(self) -> QWidget:
        """تب نمای کلی با KPI Cards و نمودارها"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # === KPI Cards ===
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)

        self.kpi_total_lines = self.create_kpi_card("📏 Total Lines", "0", "#3498db")
        self.kpi_overall_progress = self.create_kpi_card("✅ Overall Progress", "0%", "#2ecc71")
        self.kpi_shortage_items = self.create_kpi_card("🔴 Shortage Items", "0", "#e74c3c")

        kpi_layout.addWidget(self.kpi_total_lines)
        kpi_layout.addWidget(self.kpi_overall_progress)
        kpi_layout.addWidget(self.kpi_shortage_items)

        layout.addLayout(kpi_layout)

        # === Charts ===
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(15)

        # نمودار میله‌ای: توزیع پیشرفت خطوط
        self.bar_chart_canvas = self.create_matplotlib_canvas()
        bar_frame = self.create_chart_frame("📈 Line Progress Distribution", self.bar_chart_canvas)
        charts_layout.addWidget(bar_frame, 60)  # 60% عرض

        # نمودار دایره‌ای: مصرف بر اساس نوع
        self.pie_chart_canvas = self.create_matplotlib_canvas()
        pie_frame = self.create_chart_frame("🥧 Material Usage by Type", self.pie_chart_canvas)
        charts_layout.addWidget(pie_frame, 40)  # 40% عرض

        layout.addLayout(charts_layout, 1)

        # ✅ دکمه‌های Export
        export_layout = QHBoxLayout()
        export_layout.addStretch()

        export_excel_btn = QPushButton("📊 Export to Excel")
        export_excel_btn.setFont(QFont("Arial", 10))
        export_excel_btn.setStyleSheet("background-color: #28a745; color: white; padding: 8px 16px;")
        export_excel_btn.clicked.connect(lambda: self.export_dashboard_data("excel"))
        export_layout.addWidget(export_excel_btn)

        export_pdf_btn = QPushButton("📄 Export to PDF")
        export_pdf_btn.setFont(QFont("Arial", 10))
        export_pdf_btn.setStyleSheet("background-color: #dc3545; color: white; padding: 8px 16px;")
        export_pdf_btn.clicked.connect(lambda: self.export_dashboard_data("pdf"))
        export_layout.addWidget(export_pdf_btn)

        layout.addLayout(export_layout)

        return tab

    def create_kpi_card(self, title: str, value: str, color: str) -> QFrame:
        """ساخت یک کارت KPI"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 10px;
                padding: 15px;
            }}
            QLabel {{
                color: white;
                background: transparent;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setObjectName("kpi_value")  # برای آپدیت بعدی

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addStretch()

        return frame

    def create_matplotlib_canvas(self) -> FigureCanvas:
        """ساخت یک Canvas برای نمودار matplotlib"""
        fig = Figure(figsize=(6, 4), dpi=100)
        canvas = FigureCanvas(fig)
        canvas.setMinimumSize(400, 300)
        return canvas

    def create_chart_frame(self, title: str, canvas: FigureCanvas) -> QFrame:
        """ساخت یک فریم برای نمودار"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title_label)
        layout.addWidget(canvas)

        return frame

    # ========================================================================
    # TAB 2: LINES STATUS
    # ========================================================================

    def create_lines_tab(self) -> QWidget:
        """تب وضعیت خطوط با جدول و فیلتر"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # === فیلتر و جستجو ===
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        search_label = QLabel("🔍 Search:")
        search_label.setFont(QFont("Arial", 10))
        filter_layout.addWidget(search_label)

        self.search_line_input = QLineEdit()
        self.search_line_input.setPlaceholderText("Enter Line No...")
        self.search_line_input.setFont(QFont("Arial", 10))
        self.search_line_input.textChanged.connect(self.filter_lines_table)
        filter_layout.addWidget(self.search_line_input, 3)

        status_label = QLabel("📊 Status:")
        status_label.setFont(QFont("Arial", 10))
        filter_layout.addWidget(status_label)

        self.status_filter = QComboBox()
        # ✅ Sort ComboBox
        sort_label = QLabel("🔽 Sort by:")
        sort_label.setFont(QFont("Arial", 10))
        filter_layout.addWidget(sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Progress (%) ↓",
            "Progress (%) ↑",
            "Line No ↑",
            "Line No ↓"
        ])
        self.sort_combo.setFont(QFont("Arial", 10))
        self.sort_combo.currentTextChanged.connect(self.update_lines_tab)
        filter_layout.addWidget(self.sort_combo, 2)

        self.status_filter.addItems(["All", "Complete", "In-Progress"])
        self.status_filter.setFont(QFont("Arial", 10))
        self.status_filter.currentTextChanged.connect(self.filter_lines_table)
        filter_layout.addWidget(self.status_filter, 2)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # === جدول خطوط ===
        self.lines_table = QTableWidget()
        self.lines_table.setColumnCount(5)
        self.lines_table.setHorizontalHeaderLabels([
            "Line No", "Progress", "Status", "Last Activity", "Actions"
        ])

        # تنظیمات جدول
        self.lines_table.setFont(QFont("Arial", 10))
        self.lines_table.setAlternatingRowColors(True)
        self.lines_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.lines_table.horizontalHeader().setFont(QFont("Arial", 10, QFont.Weight.Bold))

        # تنظیم عرض ستون‌ها
        header = self.lines_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Line No
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # Progress
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Last Activity
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Actions

        self.lines_table.setColumnWidth(1, 200)  # عرض Progress Bar
        self.lines_table.setColumnWidth(4, 80)  # عرض دکمه Actions

        layout.addWidget(self.lines_table, 1)

        return tab

    # ========================================================================
    # TAB 3: MATERIAL ANALYSIS
    # ========================================================================

    def create_materials_tab(self) -> QWidget:
        """تب تحلیل متریال با MTO Summary و Shortage"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # === فیلتر MTO ===
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        item_code_label = QLabel("🔤 Item Code:")
        filter_layout.addWidget(item_code_label)

        self.mto_item_code_filter = QLineEdit()
        self.mto_item_code_filter.setPlaceholderText("Filter by Item Code...")
        filter_layout.addWidget(self.mto_item_code_filter, 2)

        desc_label = QLabel("📝 Description:")
        filter_layout.addWidget(desc_label)

        self.mto_desc_filter = QLineEdit()
        self.mto_desc_filter.setPlaceholderText("Filter by Description...")
        filter_layout.addWidget(self.mto_desc_filter, 3)

        apply_filter_btn = QPushButton("🔍 Apply Filter")
        apply_filter_btn.clicked.connect(self.apply_mto_filter)
        filter_layout.addWidget(apply_filter_btn)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # === MTO Summary Table ===
        summary_label = QLabel("📋 MTO Summary")
        summary_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(summary_label)

        self.mto_table = QTableWidget()
        self.mto_table.setColumnCount(7)
        self.mto_table.setHorizontalHeaderLabels([
            "Item Code", "Description", "Unit", "Total Required", "Total Used", "Remaining", "Progress %"
        ])
        self.mto_table.setFont(QFont("Arial", 9))
        self.mto_table.setAlternatingRowColors(True)
        self.mto_table.horizontalHeader().setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.mto_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.mto_table, 2)

        # === Shortage Section ===
        shortage_label = QLabel("🔴 Shortage Items")
        shortage_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        shortage_label.setStyleSheet("color: #e74c3c;")
        layout.addWidget(shortage_label)

        self.shortage_table = QTableWidget()
        self.shortage_table.setColumnCount(6)
        self.shortage_table.setHorizontalHeaderLabels([
            "Item Code", "Description", "Total Required", "Total Used", "Remaining", "Progress %"
        ])
        self.shortage_table.setFont(QFont("Arial", 9))
        self.shortage_table.setAlternatingRowColors(True)
        self.shortage_table.horizontalHeader().setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.shortage_table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.shortage_table, 1)

        # === Export Buttons ===
        export_layout = QHBoxLayout()
        export_layout.addStretch()

        export_excel_btn = QPushButton("📥 Export to Excel")
        export_excel_btn.setFont(QFont("Arial", 10))
        export_excel_btn.clicked.connect(lambda: self.export_mto_data("excel"))
        export_layout.addWidget(export_excel_btn)

        export_pdf_btn = QPushButton("📄 Export to PDF")
        export_pdf_btn.setFont(QFont("Arial", 10))
        export_pdf_btn.clicked.connect(lambda: self.export_mto_data("pdf"))
        export_layout.addWidget(export_pdf_btn)

        layout.addLayout(export_layout)

        return tab

    # ========================================================================
    # TAB 4: ACTIVITY TIMELINE
    # ========================================================================

    def create_timeline_tab(self) -> QWidget:
        """تب تایم‌لاین فعالیت‌ها"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # === عنوان ===
        info_label = QLabel("📅 Recent Activity Timeline")
        info_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        # ✅ فیلتر تاریخ
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        from_label = QLabel("📅 From:")
        from_label.setFont(QFont("Arial", 10))
        filter_layout.addWidget(from_label)

        from datetime import datetime, timedelta
        default_start = datetime.now() - timedelta(days=30)

        self.timeline_start_date = QDateEdit()
        self.timeline_start_date.setDate(QDate(default_start.year, default_start.month, default_start.day))
        self.timeline_start_date.setCalendarPopup(True)
        self.timeline_start_date.setFont(QFont("Arial", 9))
        filter_layout.addWidget(self.timeline_start_date)

        to_label = QLabel("📅 To:")
        to_label.setFont(QFont("Arial", 10))
        filter_layout.addWidget(to_label)

        self.timeline_end_date = QDateEdit()
        self.timeline_end_date.setDate(QDate.currentDate())
        self.timeline_end_date.setCalendarPopup(True)
        self.timeline_end_date.setFont(QFont("Arial", 9))
        filter_layout.addWidget(self.timeline_end_date)

        apply_filter_btn = QPushButton("🔍 Apply")
        apply_filter_btn.setFont(QFont("Arial", 9))
        apply_filter_btn.clicked.connect(self.update_timeline_tab)
        filter_layout.addWidget(apply_filter_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # === نمودار روند مصرف ===
        self.timeline_chart_canvas = self.create_matplotlib_canvas()
        chart_frame = self.create_chart_frame("📈 MIV Registration Trend", self.timeline_chart_canvas)
        layout.addWidget(chart_frame, 1)

        # === جدول آخرین فعالیت‌ها ===
        activity_label = QLabel("🕒 Recent MIV Activities")
        activity_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(activity_label)

        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(6)
        self.activity_table.setHorizontalHeaderLabels([
            "Date & Time", "MIV Tag", "Line No", "Registered By", "Status", "Comment"
        ])

        self.activity_table.setFont(QFont("Arial", 9))
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.horizontalHeader().setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.activity_table.horizontalHeader().setStretchLastSection(True)
        self.activity_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.activity_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.activity_table, 2)

        # === دکمه Refresh ===
        refresh_btn = QPushButton("🔄 Refresh Timeline")
        refresh_btn.setFont(QFont("Arial", 10))
        refresh_btn.clicked.connect(self.update_timeline_tab)
        layout.addWidget(refresh_btn)

        return tab

    def update_timeline_tab(self):
        """آپدیت تب Activity Timeline با فیلتر تاریخ"""
        try:
            from datetime import datetime

            # ✅ دریافت بازه زمانی از فیلتر
            start_qdate = self.timeline_start_date.date()
            end_qdate = self.timeline_end_date.date()

            start_date = datetime(start_qdate.year(), start_qdate.month(), start_qdate.day())
            end_date = datetime(end_qdate.year(), end_qdate.month(), end_qdate.day(), 23, 59, 59)

            # دریافت MIV ها در بازه زمانی
            session = self.dm.get_session()
            try:
                from models import MIVRecord

                recent_mivs = session.query(MIVRecord).filter(
                    MIVRecord.project_id == self.project_id,
                    MIVRecord.last_updated >= start_date,
                    MIVRecord.last_updated <= end_date
                ).order_by(MIVRecord.last_updated.desc()).limit(100).all()

                # آپدیت جدول
                self.activity_table.setRowCount(len(recent_mivs))

                for row_idx, miv in enumerate(recent_mivs):
                    # تاریخ و ساعت
                    date_item = QTableWidgetItem(miv.last_updated.strftime('%Y-%m-%d %H:%M'))
                    date_item.setFont(QFont("Arial", 9))
                    self.activity_table.setItem(row_idx, 0, date_item)

                    # MIV Tag
                    tag_item = QTableWidgetItem(miv.miv_tag)
                    tag_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                    self.activity_table.setItem(row_idx, 1, tag_item)

                    # Line No
                    line_item = QTableWidgetItem(miv.line_no)
                    self.activity_table.setItem(row_idx, 2, line_item)

                    # Registered By
                    user_item = QTableWidgetItem(miv.registered_by)
                    self.activity_table.setItem(row_idx, 3, user_item)

                    # Status
                    status_item = QTableWidgetItem(miv.status)
                    if miv.status.lower() in ['approved', 'complete']:
                        status_item.setForeground(QColor("#2ecc71"))
                    elif miv.status.lower() in ['pending', 'in-progress']:
                        status_item.setForeground(QColor("#f39c12"))
                    else:
                        status_item.setForeground(QColor("#e74c3c"))
                    self.activity_table.setItem(row_idx, 4, status_item)

                    # Comment
                    comment = (miv.comment[:50] + "...") if miv.comment and len(miv.comment) > 50 else (
                                miv.comment or "")
                    comment_item = QTableWidgetItem(comment)
                    comment_item.setFont(QFont("Arial", 8))
                    self.activity_table.setItem(row_idx, 5, comment_item)

                # رسم نمودار روند
                self.plot_timeline_chart(recent_mivs, start_date, end_date)

                logging.info(
                    f"✅ Timeline updated: {len(recent_mivs)} activities from {start_date.date()} to {end_date.date()}")

            finally:
                session.close()

        except Exception as e:
            logging.error(f"❌ Error updating timeline: {e}")
            import traceback
            logging.error(traceback.format_exc())

    def plot_timeline_chart(self, recent_mivs, start_date, end_date):
        """رسم نمودار روند ثبت MIV در بازه زمانی مشخص"""
        fig = self.timeline_chart_canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)

        try:
            from datetime import timedelta
            from collections import defaultdict

            if not recent_mivs:
                ax.text(0.5, 0.5, 'No Activity Data', ha='center', va='center', fontsize=12, color='gray')
                self.timeline_chart_canvas.draw()
                return

            # ✅ حذف timezone
            if hasattr(start_date, 'tzinfo') and start_date.tzinfo is not None:
                start_date = start_date.replace(tzinfo=None)
            if hasattr(end_date, 'tzinfo') and end_date.tzinfo is not None:
                end_date = end_date.replace(tzinfo=None)

            # شمارش MIV ها بر اساس روز
            daily_counts = defaultdict(int)

            for miv in recent_mivs:
                miv_date = miv.last_updated
                if hasattr(miv_date, 'tzinfo') and miv_date.tzinfo is not None:
                    miv_date = miv_date.replace(tzinfo=None)

                if start_date <= miv_date <= end_date:
                    date_key = miv_date.strftime('%Y-%m-%d')
                    daily_counts[date_key] += 1

            sorted_dates = sorted(daily_counts.keys())
            counts = [daily_counts[date] for date in sorted_dates]

            if not sorted_dates:
                ax.text(0.5, 0.5, 'No Activity in Range', ha='center', va='center', fontsize=12, color='gray')
                self.timeline_chart_canvas.draw()
                return

            # رسم نمودار
            ax.plot(range(len(sorted_dates)), counts, marker='o', linewidth=2, color='#3498db', markersize=6)
            ax.fill_between(range(len(sorted_dates)), counts, alpha=0.3, color='#3498db')

            ax.set_xlabel('Date', fontsize=10, fontweight='bold')
            ax.set_ylabel('Number of MIVs', fontsize=10, fontweight='bold')
            ax.set_title(f'MIV Registration Trend ({start_date.date()} to {end_date.date()})',
                         fontsize=11, fontweight='bold', pad=10)

            step = max(1, len(sorted_dates) // 6)
            ax.set_xticks(range(0, len(sorted_dates), step))
            ax.set_xticklabels([sorted_dates[i][5:] for i in range(0, len(sorted_dates), step)], rotation=45,
                               fontsize=8)

            ax.grid(axis='y', alpha=0.3, linestyle='--')

            fig.tight_layout()
            self.timeline_chart_canvas.draw()

            logging.info(f"✅ Timeline chart: {len(sorted_dates)} days, {sum(counts)} MIVs")

        except Exception as e:
            logging.error(f"❌ Error plotting timeline chart: {e}")
            import traceback
            logging.error(traceback.format_exc())
            ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', fontsize=10, color='red')
            self.timeline_chart_canvas.draw()

    # ========================================================================
    # DATA LOADING
    # ========================================================================

    def load_all_data(self):
        """بارگذاری تمام داده‌ها از DataManager (Async)"""
        try:
            # ✅ نمایش Loading Overlay
            self.show_loading_overlay()

            # ✅ شروع Thread
            self.worker = DataLoadWorker(self.dm, self.project_id)
            self.worker.finished.connect(self.on_data_loaded)
            self.worker.error.connect(self.on_data_load_error)
            self.worker.start()

        except Exception as e:
            logging.error(f"❌ Error starting data load: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start loading:\n{e}")

    def on_data_loaded(self, data):
        """اتمام بارگذاری موفق"""
        self.project_progress = data['project_progress']
        self.lines_data = data['lines_data']
        self.mto_summary = data['mto_summary']
        self.shortage_data = data['shortage_data']

        # آپدیت UI
        self.update_overview_tab()
        self.update_lines_tab()
        self.update_materials_tab()
        self.update_timeline_tab()

        self.hide_loading_overlay()
        logging.info("✅ All dashboard data loaded successfully.")

    def on_data_load_error(self, error_msg):
        """خطا در بارگذاری"""
        self.hide_loading_overlay()
        logging.error(f"❌ Data load error: {error_msg}")
        QMessageBox.critical(self, "Error", f"Failed to load data:\n{error_msg}")

    def show_loading_overlay(self):
        """نمایش پنجره بارگذاری"""
        if not hasattr(self, 'loading_label'):
            self.loading_label = QLabel("⏳ Loading Dashboard...", self)
            self.loading_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 0, 0, 180);
                    color: white;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 20px;
                    border-radius: 10px;
                }
            """)
            self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.loading_label.setGeometry(self.rect())
        self.loading_label.show()
        self.loading_label.raise_()

    def hide_loading_overlay(self):
        """مخفی کردن Overlay"""
        if hasattr(self, 'loading_label'):
            self.loading_label.hide()

    def update_overview_tab(self):
        """آپدیت تب Overview"""
        # آپدیت KPI Cards
        total_lines = self.project_progress.get("total_lines", 0)
        overall_percentage = self.project_progress.get("percentage", 0)
        shortage_count = len(self.shortage_data.get("data", []))

        self.kpi_total_lines.findChild(QLabel, "kpi_value").setText(str(total_lines))
        self.kpi_overall_progress.findChild(QLabel, "kpi_value").setText(f"{overall_percentage:.1f}%")
        self.kpi_shortage_items.findChild(QLabel, "kpi_value").setText(str(shortage_count))

        # رسم نمودار میله‌ای
        self.plot_bar_chart()

        # رسم نمودار دایره‌ای
        self.plot_pie_chart()

    def plot_bar_chart(self):
        """رسم نمودار میله‌ای توزیع پیشرفت خطوط (15 برتر)"""
        fig = self.bar_chart_canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)

        if not self.lines_data:
            ax.text(0.5, 0.5, 'No Data Available', ha='center', va='center', fontsize=12, color='gray')
            self.bar_chart_canvas.draw()
            return

        # ✅ مرتب‌سازی بر اساس Progress (نزولی) - برترین‌ها اول
        sorted_lines = sorted(self.lines_data, key=lambda x: x.get("Progress (%)", 0), reverse=True)

        # ✅ انتخاب 15 خط برتر (با بیشترین پیشرفت)
        display_lines = sorted_lines[:15]

        # ✅ برای نمایش بهتر، آن‌ها را بر اساس Progress مرتب می‌کنیم (صعودی برای نمودار افقی)
        display_lines.sort(key=lambda x: x.get("Progress (%)", 0))

        line_names = [item["Line No"] for item in display_lines]
        progress_values = [item["Progress (%)"] for item in display_lines]

        # رنگ‌بندی بر اساس درصد پیشرفت
        colors = ['#2ecc71' if p >= 80 else '#f39c12' if p >= 50 else '#e74c3c' for p in progress_values]

        bars = ax.barh(line_names, progress_values, color=colors, edgecolor='black', linewidth=0.5)

        # افزودن مقادیر روی میله‌ها
        for bar in bars:
            width = bar.get_width()
            if width > 0:  # ✅ فقط برای مقادیر غیر صفر
                ax.text(width + 1, bar.get_y() + bar.get_height() / 2, f'{width:.1f}%',
                        ha='left', va='center', fontsize=8, fontweight='bold')

        ax.set_xlabel('Progress (%)', fontsize=10, fontweight='bold')
        ax.set_xlim(0, 110)
        ax.set_title('Top 15 Lines by Progress (Highest First)', fontsize=11, fontweight='bold', pad=10)
        ax.grid(axis='x', alpha=0.3, linestyle='--')

        fig.tight_layout()
        self.bar_chart_canvas.draw()

        logging.info(f"✅ Bar chart plotted: {len(display_lines)} lines")

    def plot_pie_chart(self):
        """رسم نمودار دایره‌ای مصرف بر اساس نوع متریال"""
        fig = self.pie_chart_canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)

        try:
            # ✅ دریافت داده به صورت مستقیم از mto_summary
            if not self.mto_summary:
                ax.text(0.5, 0.5, 'No Data Available', ha='center', va='center', fontsize=12, color='gray')
                self.pie_chart_canvas.draw()
                return

            # ✅ استخراج صحیح data
            if isinstance(self.mto_summary, dict):
                data = self.mto_summary.get("data", [])
            elif isinstance(self.mto_summary, list):
                data = self.mto_summary
            else:
                logging.error(f"❌ Unexpected mto_summary type: {type(self.mto_summary)}")
                ax.text(0.5, 0.5, 'Invalid Data Format', ha='center', va='center', fontsize=12, color='red')
                self.pie_chart_canvas.draw()
                return

            if not data:
                ax.text(0.5, 0.5, 'No Material Consumption', ha='center', va='center', fontsize=12, color='gray')
                self.pie_chart_canvas.draw()
                return

            # ✅ گروه‌بندی بر اساس Item Code
            usage_by_type = {}
            for item in data:
                try:
                    if not isinstance(item, dict):
                        logging.warning(f"⚠️ Skipping non-dict item: {type(item)}")
                        continue

                    item_code = str(item.get("Item Code", "Unknown"))
                    used = float(item.get("Total Used", 0))

                    if used <= 0:
                        continue

                    if item_code not in usage_by_type:
                        usage_by_type[item_code] = 0
                    usage_by_type[item_code] += used

                except (ValueError, TypeError, KeyError) as e:
                    logging.warning(f"⚠️ Skipping invalid item: {e}")
                    continue

            if not usage_by_type:
                ax.text(0.5, 0.5, 'No Consumption Data', ha='center', va='center', fontsize=12, color='gray')
                self.pie_chart_canvas.draw()
                return

            # ✅ مرتب‌سازی و محدود به 8 آیتم برتر
            sorted_items = sorted(usage_by_type.items(), key=lambda x: x[1], reverse=True)[:8]

            # اگر بیش از 8 باشد، بقیه را در "Others" جمع کن
            if len(usage_by_type) > 8:
                others_sum = sum(v for k, v in usage_by_type.items()
                                 if k not in [item[0] for item in sorted_items])
                if others_sum > 0:
                    sorted_items.append(("Others", others_sum))

            labels = [item[0][:20] + "..." if len(item[0]) > 20 else item[0] for item in sorted_items]
            sizes = [item[1] for item in sorted_items]

            # ✅ رسم نمودار
            colors = plt.cm.Set3.colors
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                textprops={'fontsize': 9}
            )

            # استایل متن‌ها
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')

            ax.set_title('Material Usage Distribution', fontsize=11, fontweight='bold', pad=10)
            ax.axis('equal')

            fig.tight_layout()
            self.pie_chart_canvas.draw()

            logging.info(f"✅ Pie chart plotted: {len(labels)} categories")

        except Exception as e:
            logging.error(f"❌ Error plotting pie chart: {e}")
            import traceback
            logging.error(traceback.format_exc())
            ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', fontsize=10, color='red')
            self.pie_chart_canvas.draw()

    def plot_material_distribution(self):
        """رسم نمودار دایره‌ای توزیع مصرف متریال (با رفع خطای string indices)"""
        self.materials_ax.clear()

        try:
            # ✅ استخراج صحیح data از ساختار دیکشنری
            if not self.mto_summary:
                self.materials_ax.text(0.5, 0.5, 'No data available',
                                       ha='center', va='center', fontsize=14)
                self.materials_canvas.draw()
                return

            # ✅ چک کردن نوع داده
            if isinstance(self.mto_summary, dict):
                data = self.mto_summary.get("data", [])
            elif isinstance(self.mto_summary, list):
                data = self.mto_summary
            else:
                logging.error(f"Unexpected mto_summary type: {type(self.mto_summary)}")
                self.materials_ax.text(0.5, 0.5, 'Invalid data format',
                                       ha='center', va='center', fontsize=14, color='red')
                self.materials_canvas.draw()
                return

            if not data:
                self.materials_ax.text(0.5, 0.5, 'No material consumption',
                                       ha='center', va='center', fontsize=14)
                self.materials_canvas.draw()
                return

            # ✅ گروه‌بندی بر اساس Item Code با مدیریت خطا
            usage_by_type = {}
            for item in data:
                try:
                    # ✅ اطمینان از اینکه item یک dict است
                    if not isinstance(item, dict):
                        continue

                    item_code = str(item.get("Item Code", "Unknown"))
                    used = float(item.get("Total Used", 0))

                    if used <= 0:  # فقط موارد مصرف‌شده
                        continue

                    if item_code not in usage_by_type:
                        usage_by_type[item_code] = 0
                    usage_by_type[item_code] += used

                except (ValueError, TypeError, KeyError) as e:
                    logging.warning(f"Skipping invalid item in pie chart: {e}")
                    continue

            if not usage_by_type:
                self.materials_ax.text(0.5, 0.5, 'No consumption data to display',
                                       ha='center', va='center', fontsize=12)
                self.materials_canvas.draw()
                return

            # ✅ مرتب‌سازی و محدود به 8 آیتم برتر
            sorted_items = sorted(usage_by_type.items(), key=lambda x: x[1], reverse=True)[:8]

            # اگر بیش از 8 آیتم باشد، بقیه را در "Others" جمع کن
            if len(usage_by_type) > 8:
                others_sum = sum(v for k, v in usage_by_type.items()
                                 if k not in [item[0] for item in sorted_items])
                sorted_items.append(("Others", others_sum))

            labels = [item[0][:20] + "..." if len(item[0]) > 20 else item[0] for item in sorted_items]
            sizes = [item[1] for item in sorted_items]

            # رسم نمودار با رنگ‌های متنوع
            colors = plt.cm.Set3(range(len(labels)))
            wedges, texts, autotexts = self.materials_ax.pie(
                sizes,
                labels=labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                textprops={'fontsize': 9}
            )

            # استایل بهتر برای درصدها
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_weight('bold')

            self.materials_ax.set_title(
                "Material Consumption Distribution",
                fontsize=12,
                weight='bold',
                pad=10
            )

            self.materials_canvas.draw()
            logging.info(f"✅ Pie chart plotted successfully with {len(labels)} categories")

        except Exception as e:
            logging.error(f"Error plotting pie chart: {e}")
            import traceback
            logging.error(traceback.format_exc())
            self.materials_ax.text(0.5, 0.5, f'Chart error:\n{str(e)}',
                                   ha='center', va='center', fontsize=10, color='red',
                                   wrap=True)
            self.materials_canvas.draw()

    def update_lines_tab(self):
        """آپدیت جدول خطوط"""
        # ✅ مرتب‌سازی بر اساس انتخاب کاربر
        sort_option = self.sort_combo.currentText()

        if sort_option == "Progress (%) ↓":
            self.lines_data.sort(key=lambda x: x["Progress (%)"], reverse=True)
        elif sort_option == "Progress (%) ↑":
            self.lines_data.sort(key=lambda x: x["Progress (%)"], reverse=False)
        elif sort_option == "Line No ↑":
            self.lines_data.sort(key=lambda x: x["Line No"])
        elif sort_option == "Line No ↓":
            self.lines_data.sort(key=lambda x: x["Line No"], reverse=True)
        self.lines_table.setRowCount(0)

        for row_idx, line_data in enumerate(self.lines_data):
            self.lines_table.insertRow(row_idx)

            # Line No
            line_no_item = QTableWidgetItem(line_data["Line No"])
            line_no_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.lines_table.setItem(row_idx, 0, line_no_item)

            # Progress Bar
            progress_value = line_data["Progress (%)"]
            progress_bar = QProgressBar()
            progress_bar.setValue(int(progress_value))
            progress_bar.setFormat(f"{progress_value:.1f}%")
            progress_bar.setFont(QFont("Arial", 9))

            # رنگ‌بندی بر اساس پیشرفت
            if progress_value >= 80:
                progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
            elif progress_value >= 50:
                progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #f39c12; }")
            else:
                progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")

            self.lines_table.setCellWidget(row_idx, 1, progress_bar)

            # Status
            status = line_data["Status"]
            status_item = QTableWidgetItem(f"{'✅' if status == 'Complete' else '🟡'} {status}")
            status_item.setFont(QFont("Arial", 10))
            self.lines_table.setItem(row_idx, 2, status_item)

            # Last Activity
            last_activity = line_data.get("Last Activity Date", "N/A")
            activity_item = QTableWidgetItem(last_activity)
            activity_item.setFont(QFont("Arial", 9))
            self.lines_table.setItem(row_idx, 3, activity_item)

            # Actions Button
            view_btn = QPushButton("👁️ View")
            view_btn.setFont(QFont("Arial", 9))
            view_btn.clicked.connect(lambda checked, ln=line_data["Line No"]: self.view_line_details(ln))
            self.lines_table.setCellWidget(row_idx, 4, view_btn)

    def filter_lines_table(self):
        """فیلتر کردن جدول خطوط"""
        search_text = self.search_line_input.text().lower()
        status_filter = self.status_filter.currentText()

        for row in range(self.lines_table.rowCount()):
            line_no = self.lines_table.item(row, 0).text().lower()
            status = self.lines_table.item(row, 2).text()

            # بررسی شرایط فیلتر
            match_search = search_text in line_no
            match_status = (status_filter == "All" or
                            (status_filter == "Complete" and "Complete" in status) or
                            (status_filter == "In-Progress" and "Progress" in status))

            # نمایش یا مخفی کردن سطر
            self.lines_table.setRowHidden(row, not (match_search and match_status))

    def update_materials_tab(self):
        """آپدیت تب متریال"""
        # آپدیت MTO Summary Table
        mto_data = self.mto_summary.get("data", [])
        self.mto_table.setRowCount(len(mto_data))

        for row_idx, item in enumerate(mto_data):
            self.mto_table.setItem(row_idx, 0, QTableWidgetItem(item["Item Code"]))
            self.mto_table.setItem(row_idx, 1, QTableWidgetItem(item["Description"]))
            self.mto_table.setItem(row_idx, 2, QTableWidgetItem(item["Unit"]))
            self.mto_table.setItem(row_idx, 3, QTableWidgetItem(f"{item['Total Required']:.2f}"))
            self.mto_table.setItem(row_idx, 4, QTableWidgetItem(f"{item['Total Used']:.2f}"))
            self.mto_table.setItem(row_idx, 5, QTableWidgetItem(f"{item['Remaining']:.2f}"))

            progress_item = QTableWidgetItem(f"{item['Progress (%)']:.1f}%")
            progress_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))

            # رنگ‌بندی
            if item['Progress (%)'] >= 80:
                progress_item.setForeground(QColor("#2ecc71"))
            elif item['Progress (%)'] >= 50:
                progress_item.setForeground(QColor("#f39c12"))
            else:
                progress_item.setForeground(QColor("#e74c3c"))

            self.mto_table.setItem(row_idx, 6, progress_item)

        # آپدیت Shortage Table
        shortage_data = self.shortage_data.get("data", [])
        self.shortage_table.setRowCount(len(shortage_data))

        for row_idx, item in enumerate(shortage_data):
            self.shortage_table.setItem(row_idx, 0, QTableWidgetItem(item["Item Code"]))
            self.shortage_table.setItem(row_idx, 1, QTableWidgetItem(item["Description"]))
            self.shortage_table.setItem(row_idx, 2, QTableWidgetItem(f"{item['Total Required']:.2f}"))
            self.shortage_table.setItem(row_idx, 3, QTableWidgetItem(f"{item['Total Used']:.2f}"))

            remaining_item = QTableWidgetItem(f"{item['Remaining']:.2f}")
            remaining_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            remaining_item.setForeground(QColor("#e74c3c"))
            self.shortage_table.setItem(row_idx, 4, remaining_item)

            progress_item = QTableWidgetItem(f"{item['Progress (%)']:.1f}%")
            progress_item.setFont(QFont("Arial", 9))
            self.shortage_table.setItem(row_idx, 5, progress_item)

    def apply_mto_filter(self):
        """اعمال فیلتر روی MTO Summary"""
        item_code_text = self.mto_item_code_filter.text().strip()
        desc_text = self.mto_desc_filter.text().strip()

        filters = {}
        if item_code_text:
            filters['item_code'] = item_code_text
        if desc_text:
            filters['description'] = desc_text

        try:
            # دریافت داده‌های فیلتر شده
            self.mto_summary = self.dm.get_project_mto_summary(self.project_id, **filters)
            self.update_materials_tab()

            logging.info(f"✅ MTO filter applied: {filters}")

        except Exception as e:
            logging.error(f"❌ Error applying MTO filter: {e}")
            QMessageBox.warning(self, "Filter Error", f"Failed to apply filter:\n{e}")

    def view_line_details(self, line_no: str):
        """نمایش جزئیات یک خط خاص"""
        try:
            details = self.dm.get_detailed_line_report(self.project_id, line_no)

            if not details or not details.get("bill_of_materials"):
                QMessageBox.information(self, "No Data", f"No details found for Line: {line_no}")
                return

            # ساخت دیالوگ نمایش جزئیات
            detail_dialog = QDialog(self)
            detail_dialog.setWindowTitle(f"📋 Line Details - {line_no}")
            detail_dialog.setMinimumSize(1000, 600)

            layout = QVBoxLayout(detail_dialog)

            title = QLabel(f"🔍 Detailed Material Status for Line: {line_no}")
            title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title)

            # جدول Bill of Materials
            bom_label = QLabel("📦 Bill of Materials")
            bom_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            layout.addWidget(bom_label)

            bom_table = QTableWidget()
            bom_data = details["bill_of_materials"]

            if bom_data:
                bom_table.setColumnCount(len(bom_data[0]))
                bom_table.setHorizontalHeaderLabels(list(bom_data[0].keys()))
                bom_table.setRowCount(len(bom_data))

                for row_idx, item in enumerate(bom_data):
                    for col_idx, (key, value) in enumerate(item.items()):
                        bom_table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

                bom_table.horizontalHeader().setStretchLastSection(True)

            layout.addWidget(bom_table)

            # دکمه بستن
            close_btn = QPushButton("✖ Close")
            close_btn.clicked.connect(detail_dialog.close)
            layout.addWidget(close_btn)

            detail_dialog.exec()

        except Exception as e:
            logging.error(f"Error viewing line details: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load line details:\n{e}")

    def export_mto_data(self, format_type: str):
        """اکسپورت داده‌های MTO به اکسل یا PDF"""
        if not self.mto_summary or not self.mto_summary.get("data"):
            QMessageBox.warning(self, "No Data", "No MTO data available to export.")
            return

        # انتخاب مسیر ذخیره
        ext = "xlsx" if format_type == "excel" else "pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save MTO Report",
            f"MTO_Summary_{self.project.name}.{ext}",
            f"{'Excel Files (*.xlsx)' if format_type == 'excel' else 'PDF Files (*.pdf)'}"
        )

        if not file_path:
            return

        try:
            # استفاده از متد export_data_to_file در DataManager
            data_to_export = self.mto_summary["data"]
            report_title = f"MTO Summary Report - {self.project.name}"

            success, message = self.dm.export_data_to_file(data_to_export, file_path, report_title)

            if success:
                QMessageBox.information(self, "Export Successful", message)
                logging.info(f"✅ MTO data exported to: {file_path}")
            else:
                QMessageBox.warning(self, "Export Failed", message)
                logging.warning(f"⚠️ Export failed: {message}")

        except Exception as e:
            logging.error(f"Error exporting MTO data: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export data:\n{e}")

    def load_lines_data(self):
        """بارگذاری داده‌های خطوط با پاک کردن cache"""
        try:
            self.lines_data = []

            # ✅ پاک کردن cache
            if hasattr(self.dm.get_line_progress, 'cache_clear'):
                self.dm.get_line_progress.cache_clear()
                logging.info("🔄 Cleared get_line_progress cache")

            # ✅ دریافت لیست خطوط
            session = self.dm.get_session()
            try:
                from models import MTOItem
                lines = session.query(MTOItem.line_no).filter(
                    MTOItem.project_id == self.project_id
                ).distinct().all()

                line_numbers = [line[0] for line in lines]
                logging.info(f"📋 Found {len(line_numbers)} unique lines")

            finally:
                session.close()

            # ✅ محاسبه پیشرفت برای هر خط
            for line_no in line_numbers:
                try:
                    # readonly=False برای rebuild در صورت نیاز
                    progress_info = self.dm.get_line_progress(
                        self.project_id,
                        line_no,
                        readonly=False
                    )

                    # دریافت آخرین فعالیت
                    session = self.dm.get_session()
                    try:
                        from models import MIVRecord
                        from sqlalchemy import func
                        last_activity = session.query(func.max(MIVRecord.last_updated)).filter(
                            MIVRecord.project_id == self.project_id,
                            MIVRecord.line_no == line_no
                        ).scalar()
                    finally:
                        session.close()

                    self.lines_data.append({
                        "Line No": line_no,
                        "Progress (%)": round(progress_info.get("percentage", 0), 2),
                        "Total (inch-dia)": round(progress_info.get("total_weight", 0), 2),
                        "Used (inch-dia)": round(progress_info.get("done_weight", 0), 2),
                        "Status": "Complete" if progress_info.get("percentage", 0) >= 99.9 else "In-Progress",
                        "Last Activity Date": last_activity.strftime('%Y-%m-%d') if last_activity else "N/A"
                    })

                except Exception as e:
                    logging.error(f"⚠️ Error loading progress for line {line_no}: {e}")
                    continue

            # ✅ مرتب‌سازی پیش‌فرض: نزولی بر اساس درصد
            self.lines_data.sort(key=lambda x: x["Progress (%)"], reverse=True)

            logging.info(f"✅ Loaded {len(self.lines_data)} lines with progress data")

        except Exception as e:
            logging.error(f"❌ Error loading lines data: {e}")
            import traceback
            logging.error(traceback.format_exc())
            self.lines_data = []

    def export_dashboard_data(self, format_type: str):
        """اکسپورت کامل داده‌های Dashboard"""
        if not self.project:
            QMessageBox.warning(self, "No Data", "No project loaded.")
            return

        ext = "xlsx" if format_type == "excel" else "pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Dashboard Report",
            f"Dashboard_Report_{self.project.name}.{ext}",
            f"{'Excel Files (*.xlsx)' if format_type == 'excel' else 'PDF Files (*.pdf)'}"
        )

        if not file_path:
            return

        try:
            import pandas as pd

            if format_type == "excel":
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    # Sheet 1: Project Overview
                    overview_data = {
                        "Project Name": [self.project.name],
                        "Total Lines": [self.project_progress.get("total_lines", 0)],
                        "Overall Progress (%)": [round(self.project_progress.get("percentage", 0), 2)],
                        "Total Weight (inch-dia)": [round(self.project_progress.get("total_weight", 0), 2)],
                        "Done Weight (inch-dia)": [round(self.project_progress.get("done_weight", 0), 2)],
                        "Shortage Items": [len(self.shortage_data.get("data", []))]
                    }
                    overview_df = pd.DataFrame(overview_data)
                    overview_df.to_excel(writer, sheet_name="Overview", index=False)

                    # Sheet 2: Lines Status
                    if self.lines_data:
                        lines_df = pd.DataFrame(self.lines_data)
                        lines_df.to_excel(writer, sheet_name="Lines Status", index=False)

                    # Sheet 3: MTO Summary
                    mto_data = self.mto_summary.get("data", [])
                    if mto_data:
                        mto_df = pd.DataFrame(mto_data)
                        mto_df.to_excel(writer, sheet_name="MTO Summary", index=False)

                    # Sheet 4: Shortage Items
                    shortage_items = self.shortage_data.get("data", [])
                    if shortage_items:
                        shortage_df = pd.DataFrame(shortage_items)
                        shortage_df.to_excel(writer, sheet_name="Shortage", index=False)

                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Dashboard exported successfully to:\n{file_path}"
                )

            else:  # PDF
                # ترکیب تمام داده‌ها برای PDF
                combined_data = []

                # افزودن Overview
                combined_data.append({
                    "Section": "Overview",
                    "Project": self.project.name,
                    "Total Lines": self.project_progress.get("total_lines", 0),
                    "Progress (%)": round(self.project_progress.get("percentage", 0), 2)
                })

                # افزودن Lines
                combined_data.extend(self.lines_data)

                success, message = self.dm.export_data_to_file(
                    combined_data,
                    file_path,
                    f"Dashboard Report - {self.project.name}"
                )

                if success:
                    QMessageBox.information(self, "Export Successful", message)
                else:
                    QMessageBox.warning(self, "Export Failed", message)

            logging.info(f"✅ Dashboard exported: {file_path}")

        except Exception as e:
            logging.error(f"Export error: {e}")
            import traceback
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Export Error", f"Failed to export dashboard:\n{e}")
