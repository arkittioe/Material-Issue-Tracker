# main_window.py

import sys
import webbrowser
import subprocess
import os
import logging

from functools import partial
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QMessageBox, QLineEdit, QSplitter, QInputDialog, QFileDialog, QDialog,
    QProgressBar, QLabel
)
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt, QStringListModel, QTimer, QDate

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from data_manager import DataManager
from models import Project, MTOItem, MIVRecord, Spool, SpoolItem
from watchdog.observers import Observer

import threading
import time
from config_manager import DB_HOST, DB_PORT, DB_NAME, ISO_PATH
from mto_consumption_dialog import MTOConsumptionDialog
from spool_manager_dialog import SpoolManagerDialog
from login_dialog import LoginDialog
from splash_screen import SplashScreen
from iso_event_handler import IsoIndexEventHandler
from iso_search_dialog import IsoSearchDialog

from ui_components import UIComponents
from event_handlers import EventHandlers


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class MainWindow(QMainWindow):
    """
    کلاس اصلی پنجره برنامه که از کامپوننت‌های UI و Event Handlers استفاده می‌کند.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("مدیریت MIV - نسخه 2.0")
        self.setGeometry(100, 100, 1200, 800)

        # --- مقداردهی اولیه متغیرها ---
        self.dm = DataManager()
        self.current_project: Project | None = None
        self.current_user = os.getlogin()
        self.suggestion_data = []
        self.dashboard_password = "hossein"

        # تایمر برای Debouncing
        self.suggestion_timer = QTimer(self)
        self.suggestion_timer.setSingleShot(True)
        self.suggestion_timer.setInterval(300)

        self.iso_observer = None

        # تنظیمات برای iso_event_handler
        config = {
            'debounce_delay': 1.0,
            'batch_size': 50,
            'batch_delay': 2.0,
            'max_retries': 3
        }

        self.iso_event_handler = IsoIndexEventHandler(self.dm)

        # --- ایجاد نمونه از کامپوننت‌ها و هندلرها ---
        self.ui_components = UIComponents(self)
        self.event_handlers = EventHandlers(self)

        # --- راه‌اندازی منو، UI و اتصال سیگنال‌ها ---
        self.setup_menu()
        self.setup_ui()
        self.connect_signals()
        self.populate_project_combo()

        QApplication.instance().aboutToQuit.connect(self.cleanup_processes)
        self.start_iso_watcher()

    def setup_menu(self):
        """راه‌اندازی منوی بالای پنجره"""
        menu_bar = self.menuBar()
        reports_menu = menu_bar.addMenu("&Reports")

        # بخش گزارش‌های وابسته به پروژه
        self.mto_summary_action = reports_menu.addAction("MTO Summary Report")
        self.line_status_action = reports_menu.addAction("Line Status List Report")
        self.shortage_action = reports_menu.addAction("Shortage Report")

        self.project_specific_actions = [
            self.mto_summary_action,
            self.line_status_action,
            self.shortage_action
        ]
        for action in self.project_specific_actions:
            action.setEnabled(False)

        reports_menu.addSeparator()

        # بخش گزارش‌های سراسری
        spool_inventory_action = reports_menu.addAction("Spool Inventory Report")
        spool_consumption_action = reports_menu.addAction("Spool Consumption History")

        # اتصال اکشن‌ها
        self.mto_summary_action.triggered.connect(
            lambda: self.event_handlers.handle_report_export('mto_summary')
        )
        self.line_status_action.triggered.connect(
            lambda: self.event_handlers.handle_report_export('line_status')
        )
        self.shortage_action.triggered.connect(
            lambda: self.event_handlers.handle_report_export('shortage')
        )
        spool_inventory_action.triggered.connect(
            lambda: self.event_handlers.handle_report_export('spool_inventory')
        )
        spool_consumption_action.triggered.connect(
            lambda: self.event_handlers.handle_report_export('spool_consumption')
        )

        # منوی Help
        help_menu = menu_bar.addMenu("&Help")

        # اضافه کردن آیکون‌ها برای زیبایی
        user_guide_action = help_menu.addAction("📖 User Guide")
        user_guide_action.setShortcut("F1")
        user_guide_action.triggered.connect(self.show_help_dialog)

        help_menu.addSeparator()

        keyboard_shortcuts_action = help_menu.addAction("⌨️ Keyboard Shortcuts")
        keyboard_shortcuts_action.triggered.connect(
            lambda: self.show_help_dialog()  # باز می‌شه روی تب Shortcuts
        )

        help_menu.addSeparator()

        about_action = help_menu.addAction("ℹ️ About MIV Manager")
        about_action.triggered.connect(self.show_about_dialog)

        check_updates_action = help_menu.addAction("🔄 Check for Updates")
        check_updates_action.triggered.connect(self._check_for_updates)

    def _check_for_updates(self):
        """بررسی نسخه جدید (می‌تونید بعداً پیاده‌سازی شود)"""
        QMessageBox.information(
            self,
            "Check for Updates",
            "You are using the latest version (2.0.0)\n\n"
            "Visit GitHub for release notes:\n"
            "https://github.com/arkittioe/Material-Issue-Tracker-SQLDB"
        )

    def setup_ui(self):
        """ساخت و چیدمان UI اصلی"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 5)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # پنل چپ
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)

        reg_form_frame = QFrame()
        reg_form_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.ui_components.create_registration_form(reg_form_frame)

        dashboard_frame = QFrame()
        dashboard_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.ui_components.create_dashboard(dashboard_frame)

        left_layout.addWidget(reg_form_frame)
        left_layout.addWidget(dashboard_frame, 1)

        # پنل راست
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        search_frame = QFrame()
        search_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.ui_components.create_search_box(search_frame)

        console_frame = QFrame()
        console_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.ui_components.create_console(console_frame)

        right_layout.addWidget(search_frame)
        right_layout.addWidget(console_frame, 1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([550, 650])

        main_layout.addWidget(splitter)

        # لیبل نام سازنده
        dev_label = QLabel("Developed by h.izadi")
        dev_label.setStyleSheet("color: #777; padding-top: 4px;")
        dev_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(dev_label)

    def connect_signals(self):
        """اتصال سیگنال‌ها به هندلرها"""
        self.load_project_btn.clicked.connect(self.load_project)
        self.register_btn.clicked.connect(self.event_handlers.handle_registration)
        self.search_btn.clicked.connect(self.event_handlers.handle_search)

        self.update_dashboard_btn.clicked.connect(
            self.event_handlers.handle_update_dashboard_button_click
        )
        self.details_btn.clicked.connect(self.show_advanced_dashboard)
        self.export_line_status_btn.clicked.connect(
            self.event_handlers.handle_line_status_export
        )

        # اتصال textChanged
        self.entries["Line No"].textChanged.connect(self.event_handlers.on_text_changed)
        self.search_entry_line.textChanged.connect(self.event_handlers.on_text_changed)

        # اتصال تایمر
        self.suggestion_timer.timeout.connect(self.event_handlers.fetch_suggestions)

        # اتصال completerها
        register_widget = self.entries["Line No"]
        self.register_completer.activated.connect(
            lambda text: self.event_handlers.on_suggestion_selected(text, register_widget)
        )

        search_widget = self.search_entry_line
        self.search_completer.activated.connect(
            lambda text: self.event_handlers.on_suggestion_selected(text, search_widget)
        )

        self.manage_spool_btn.clicked.connect(self.open_spool_manager)
        self.update_data_btn.clicked.connect(
            self.event_handlers.handle_data_update_from_csv
        )

        self.iso_search_btn.clicked.connect(self.event_handlers.handle_iso_search)

        self.iso_event_handler.status_updated.connect(self.update_iso_status_label)
        self.iso_event_handler.progress_updated.connect(self.update_iso_progress)

    def populate_project_combo(self):
        """پر کردن ComboBox پروژه‌ها"""
        self.project_combo.clear()
        try:
            projects = self.dm.get_all_projects()
            if not projects:
                self.project_combo.addItem("هیچ پروژه‌ای یافت نشد", userData=None)
            else:
                self.project_combo.addItem("همه پروژه‌ها", userData=None)
                for proj in projects:
                    self.project_combo.addItem(proj.name, userData=proj)
        except Exception as e:
            self.log_to_console(f"خطا در بارگذاری پروژه‌ها: {e}", "error")

    def load_project(self):
        """بارگذاری پروژه انتخاب شده"""
        selected_index = self.project_combo.currentIndex()
        if selected_index == -1:
            return

        project_data = self.project_combo.itemData(selected_index)
        self.current_project = project_data

        is_project_loaded = self.current_project is not None
        for action in self.project_specific_actions:
            action.setEnabled(is_project_loaded)

        if self.current_project:
            self.log_to_console(
                f"Project '{self.current_project.name}' loaded successfully.",
                "success"
            )
            self.log_to_console(
                "Project-specific reports are now enabled in the 'Reports' menu.",
                "info"
            )
        else:
            self.log_to_console(
                "Global search mode is active. Project-specific reports are disabled.",
                "info"
            )

    def update_line_dashboard(self, line_no=None):
        """بروزرسانی نمودار Pie Chart با داده‌های inch_dia"""
        if not self.current_project:
            return

        if line_no is None:
            line_no = self.entries["Line No"].text().strip()

        self.dashboard_ax.clear()

        if not line_no:
            self.dashboard_ax.text(
                0.5, 0.5,
                "Please enter the line number",
                ha='center', va='center'
            )
            self.canvas.draw()
            return

        try:
            progress = self.dm.get_line_progress(self.current_project.id, line_no, readonly=False)

            total = progress['total_weight']
            done = progress['done_weight']
            percentage = progress['percentage']

            if total > 0:
                remaining = total - done
                sizes = [done, remaining]
                labels = ['Completed', 'Remaining']
                colors = ['#28a745', '#dc3545']
                explode = (0.05, 0)

                self.dashboard_ax.pie(
                    sizes, labels=labels, autopct='%1.1f%%',
                    startangle=90, colors=colors, explode=explode
                )

                # 🆕 نمایش واحد inch-dia
                self.dashboard_ax.set_title(
                    f"Line {line_no}: {percentage:.1f}%\n"
                    f"({done:.1f} / {total:.1f} inch-dia)",
                    fontsize=14, weight='bold'
                )
            else:
                self.dashboard_ax.text(
                    0.5, 0.5, 'No Data',
                    ha='center', va='center', fontsize=16
                )

            self.canvas.draw()

        except Exception as e:
            print(f"⚠️ خطا در بروزرسانی داشبورد: {e}")  # 🔄 تغییر به print
            import traceback
            traceback.print_exc()

    def log_to_console(self, message, level="info"):
        """نمایش پیام در کنسول با رنگ‌بندی"""
        color_map = {
            "info": "#8be9fd",
            "success": "#50fa7b",
            "warning": "#f1fa8c",
            "error": "#ff5555"
        }
        color = color_map.get(level, "#f8f8f2")
        formatted_message = f'<span style="color: {color};">{message}</span>'
        self.console_output.append(formatted_message)

    def show_message(self, title, message, level="info", detailed=None):
        """نمایش پیام در MessageBox"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)

        if detailed:
            msg_box.setDetailedText(detailed)
            msg_box.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse |
                Qt.TextInteractionFlag.TextSelectableByKeyboard
            )

        icon_map = {
            "info": QMessageBox.Icon.Information,
            "warning": QMessageBox.Icon.Warning,
            "error": QMessageBox.Icon.Critical,
            "success": QMessageBox.Icon.Information
        }
        msg_box.setIcon(icon_map.get(level, QMessageBox.Icon.NoIcon))
        msg_box.exec()

    def show_advanced_dashboard(self):
        """نمایش داشبورد پیشرفته پروژه (Modeless)"""
        if not self.current_project:
            self.show_message("خطا", "لطفاً ابتدا یک پروژه را بارگذاری کنید.", "warning")
            return

        try:
            from advanced_dashboard_dialog import AdvancedDashboardDialog

            # ✅ اگر قبلاً باز شده، فوکوس بده
            if hasattr(self, 'dashboard_window') and self.dashboard_window.isVisible():
                self.dashboard_window.raise_()
                self.dashboard_window.activateWindow()
                return

            # ✅ ساخت دیالوگ Modeless
            self.dashboard_window = AdvancedDashboardDialog(
                self.dm,
                self.current_project.id,
                self
            )

            # ✅ نمایش بدون بلوک کردن پنجره اصلی
            self.dashboard_window.show()

        except Exception as e:
            self.show_message("خطا", f"خطا در باز کردن داشبورد:\n{e}", "error")
            import traceback
            logging.error(f"Error opening advanced dashboard:\n{traceback.format_exc()}")

    def open_spool_manager(self):
        """باز کردن دیالوگ مدیریت اسپول‌ها"""
        python_executable = sys.executable
        dialog = SpoolManagerDialog(self.dm, self)
        dialog.exec()

    def show_about_dialog(self):
        """نمایش پنجره درباره برنامه (نسخه جدید)"""
        from about_dialog import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec()

    def show_help_dialog(self):
        """نمایش راهنمای استفاده"""
        from about_dialog import HelpDialog
        dialog = HelpDialog(self)
        dialog.exec()

    def cleanup_processes(self):
        """پاکسازی و بستن پروسه‌های جانبی"""
        try:
            if hasattr(self, 'api_process') and self.api_process:
                self.api_process.kill()
            if hasattr(self, 'dashboard_process') and self.dashboard_process:
                self.dashboard_process.kill()

            if self.iso_observer:
                self.iso_observer.stop()
                self.iso_observer.join()
                print("ISO watcher stopped.")

        except Exception as e:
            print(f"⚠️ خطا در بستن پروسه‌ها: {e}")

    def update_iso_status_label(self, message, level):
        """به‌روزرسانی لیبل وضعیت ISO"""
        color_map = {
            "info": "#8be9fd",
            "success": "#50fa7b",
            "warning": "#f1fa8c",
            "error": "#ff5555"
        }
        color = color_map.get(level, "#f8f8f2")
        self.iso_status_label.setText(f"وضعیت ایندکس ISO: {message}")
        self.iso_status_label.setStyleSheet(f"padding: 4px; color: {color};")
        if level != "error":
            self.log_to_console(f"ISO Indexer: {message}", level)

    def start_iso_watcher(self):
        """راه‌اندازی ترد نگهبان فایل‌های ISO"""
        path = ISO_PATH
        if not os.path.isdir(path):
            self.update_iso_status_label(f"مسیر یافت نشد!", "error")
            return

        self.update_iso_status_label("در حال همگام‌سازی اولیه...", "warning")

        threading.Thread(
            target=self.dm.rebuild_iso_index_from_scratch,
            args=(path, self.iso_event_handler),
            daemon=True
        ).start()

        if self.iso_observer:
            self.iso_observer.stop()
            self.iso_observer.join()

        self.iso_observer = Observer()
        self.iso_observer.schedule(self.iso_event_handler, path, recursive=True)
        self.iso_observer.start()

    def update_iso_progress(self, value, text):
        """به‌روزرسانی نوار پیشرفت ISO"""
        if not self.iso_progress_bar.isVisible():
            self.iso_progress_bar.show()

        self.iso_progress_bar.setFormat(f"{text} %p%")
        self.iso_progress_bar.setValue(value)

        if value >= 100:
            self.iso_progress_bar.setFormat("Completed!")
            QTimer.singleShot(5000, lambda: self.iso_progress_bar.hide())


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # لاگین قبل از اسپلش
    login_dlg = LoginDialog()
    if login_dlg.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    username, password = login_dlg.get_credentials()

    os.environ["APP_DB_USER"] = username
    os.environ["APP_DB_PASSWORD"] = password

    from data_manager import DataManager

    app.data_manager = DataManager()
    app.login_user = username

    # اسپلش
    splash = SplashScreen()
    app.processEvents()


    def start_main_window():
        splash.close()
        window = MainWindow()
        window.show()
        app.window = window


    QTimer.singleShot(3000, start_main_window)


    # مدیریت خطاهای پیش‌بینی‌نشده
    def excepthook(exc_type, exc_value, exc_tb):
        import traceback
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print("Unhandled exception:", error_msg)

        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Unhandled Exception")
        box.setText("خطای غیرمنتظره رخ داد")
        box.setDetailedText(error_msg)
        box.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        box.exec()


    sys.excepthook = excepthook
    sys.exit(app.exec())
