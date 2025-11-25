# file: advanced_dashboard_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QProgressBar, QFrame, QSizePolicy,
    QMessageBox, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QPalette

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from typing import Dict, List, Any
import logging


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

        info_label = QLabel("📅 Recent Activity Timeline")
        info_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        # این بخش در مرحله 2 کامل می‌شه
        placeholder = QLabel("🚧 Coming Soon: Activity logs and consumption trends over time...")
        placeholder.setFont(QFont("Arial", 11))
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #95a5a6; padding: 50px;")
        layout.addWidget(placeholder, 1)

        return tab

    # ========================================================================
    # DATA LOADING
    # ========================================================================

    def load_all_data(self):
        """بارگذاری تمام داده‌ها از DataManager"""
        try:
            # دریافت پیشرفت کلی پروژه
            self.project_progress = self.dm.get_project_progress(self.project_id)

            # دریافت لیست خطوط
            self.lines_data = self.dm.get_project_line_status_list(self.project_id)

            # دریافت MTO Summary
            self.mto_summary = self.dm.get_project_mto_summary(self.project_id)

            # دریافت Shortage Report
            self.shortage_data = self.dm.get_shortage_report(self.project_id)

            # آپدیت UI
            self.update_overview_tab()
            self.update_lines_tab()
            self.update_materials_tab()

            logging.info("✅ All dashboard data loaded successfully.")

        except Exception as e:
            logging.error(f"❌ Error loading dashboard data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load dashboard data:\n{e}")

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
        """رسم نمودار میله‌ای توزیع پیشرفت خطوط"""
        fig = self.bar_chart_canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)

        if not self.lines_data:
            ax.text(0.5, 0.5, 'No Data Available', ha='center', va='center', fontsize=12, color='gray')
            self.bar_chart_canvas.draw()
            return

        # مرتب‌سازی بر اساس Line No
        sorted_lines = sorted(self.lines_data, key=lambda x: x.get("Line No", ""))

        # انتخاب حداکثر 15 خط برای نمایش (برای خوانایی بهتر)
        display_lines = sorted_lines[:15]

        line_names = [item["Line No"] for item in display_lines]
        progress_values = [item["Progress (%)"] for item in display_lines]

        # رنگ‌بندی بر اساس درصد پیشرفت
        colors = ['#2ecc71' if p >= 80 else '#f39c12' if p >= 50 else '#e74c3c' for p in progress_values]

        bars = ax.barh(line_names, progress_values, color=colors, edgecolor='black', linewidth=0.5)

        # افزودن مقادیر روی میله‌ها
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height() / 2, f'{width:.1f}%',
                    ha='left', va='center', fontsize=8, fontweight='bold')

        ax.set_xlabel('Progress (%)', fontsize=10, fontweight='bold')
        ax.set_xlim(0, 110)
        ax.set_title('Top 15 Lines by Progress', fontsize=11, fontweight='bold', pad=10)
        ax.grid(axis='x', alpha=0.3, linestyle='--')

        fig.tight_layout()
        self.bar_chart_canvas.draw()

    def plot_pie_chart(self):
        """رسم نمودار دایره‌ای مصرف بر اساس نوع متریال"""
        fig = self.pie_chart_canvas.figure
        fig.clear()
        ax = fig.add_subplot(111)

        try:
            # دریافت داده از get_report_analytics
            analytics_data = self.dm.get_report_analytics(
                self.project_id,
                'material_usage_by_type'
            )

            if not analytics_data or not analytics_data.get("data"):
                ax.text(0.5, 0.5, 'No Data Available', ha='center', va='center', fontsize=12, color='gray')
                self.pie_chart_canvas.draw()
                return

            # استخراج داده‌ها
            data = analytics_data["data"]
            labels = [item["item_type"] or "Unknown" for item in data]
            sizes = [item["total_used"] for item in data]

            # رنگ‌های حرفه‌ای
            colors = plt.cm.Set3.colors

            # رسم نمودار
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

        except Exception as e:
            logging.error(f"Error plotting pie chart: {e}")
            ax.text(0.5, 0.5, f'Error: {e}', ha='center', va='center', fontsize=10, color='red')
            self.pie_chart_canvas.draw()

    def plot_material_distribution(self):
        """رسم نمودار دایره‌ای توزیع مصرف متریال"""
        self.materials_ax.clear()

        try:
            # ✅ بررسی ساختار داده
            if not self.mto_summary or not isinstance(self.mto_summary, dict):
                self.materials_ax.text(0.5, 0.5, 'No data available',
                                       ha='center', va='center', fontsize=14)
                self.materials_canvas.draw()
                return

            data = self.mto_summary.get("data", [])

            if not data or not isinstance(data, list):
                self.materials_ax.text(0.5, 0.5, 'No material data',
                                       ha='center', va='center', fontsize=14)
                self.materials_canvas.draw()
                return

            # ✅ گروه‌بندی بر اساس Item Code
            usage_by_type = {}
            for item in data:
                if not isinstance(item, dict):
                    continue

                item_code = item.get("Item Code", "Unknown")
                used = item.get("Total Used", 0)

                if item_code not in usage_by_type:
                    usage_by_type[item_code] = 0
                usage_by_type[item_code] += used

            if not usage_by_type:
                self.materials_ax.text(0.5, 0.5, 'No consumption data',
                                       ha='center', va='center', fontsize=14)
                self.materials_canvas.draw()
                return

            # ✅ مرتب‌سازی و محدود کردن به 8 آیتم برتر
            sorted_items = sorted(usage_by_type.items(), key=lambda x: x[1], reverse=True)[:8]

            labels = [item[0] for item in sorted_items]
            sizes = [item[1] for item in sorted_items]

            # رسم نمودار
            colors = plt.cm.Set3(range(len(labels)))
            self.materials_ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                  startangle=90, colors=colors)
            self.materials_ax.set_title("Material Consumption Distribution (Top 8)",
                                        fontsize=12, weight='bold')

            self.materials_canvas.draw()

        except Exception as e:
            logging.error(f"Error plotting pie chart: {e}")
            import traceback
            logging.error(traceback.format_exc())
            self.materials_ax.text(0.5, 0.5, f'Chart error: {str(e)}',
                                   ha='center', va='center', fontsize=10, color='red')
            self.materials_canvas.draw()

    def update_lines_tab(self):
        """آپدیت جدول خطوط"""
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
