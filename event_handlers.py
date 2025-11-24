# event_handlers.py

from PyQt6.QtWidgets import (
    QApplication, QMessageBox, QDialog, QLineEdit, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QVBoxLayout, QHBoxLayout,
    QDialogButtonBox, QFormLayout, QPushButton, QWidget, QTabWidget, QLabel, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from functools import partial

from mto_consumption_dialog import MTOConsumptionDialog
from iso_search_dialog import IsoSearchDialog
from models import MIVRecord


class EventHandlers:
    def __init__(self, main_window):
        self.main_window = main_window

    def handle_registration(self):
        if not self.main_window.current_project:
            self.main_window.show_message("خطا", "لطفاً ابتدا یک پروژه را بارگذاری کنید.", "warning")
            return

        form_data = {field: widget.text().strip().upper() for field, widget in self.main_window.entries.items()}
        form_data["Registered By"] = self.main_window.current_user
        form_data["Complete"] = False

        if not form_data["Line No"] or not form_data["MIV Tag"]:
            self.main_window.show_message("خطا", "فیلدهای Line No و MIV Tag اجباری هستند.", "warning")
            return

        if self.main_window.dm.is_duplicate_miv_tag(form_data["MIV Tag"], self.main_window.current_project.id):
            self.main_window.show_message("خطا", f"تگ '{form_data['MIV Tag']}' در این پروژه تکراری است.", "error")
            return

        self.main_window.dm.initialize_mto_progress_for_line(self.main_window.current_project.id, form_data["Line No"])

        dialog = MTOConsumptionDialog(self.main_window.dm, self.main_window.current_project.id, form_data["Line No"], parent=self.main_window)
        if not dialog.exec():
            self.main_window.log_to_console("ثبت رکورد لغو شد.", "warning")
            return

        consumed_items, spool_items = dialog.get_data()
        if not consumed_items and not spool_items:
            self.main_window.log_to_console("ثبت رکورد لغو شد چون هیچ آیتمی مصرف نشده بود.", "warning")
            return

        comment_parts = []
        if consumed_items:
            mto_info_map = {item['mto_item_id']: item for item in dialog.progress_data}
            for item in consumed_items:
                mto_details = mto_info_map.get(item['mto_item_id'])
                if mto_details:
                    identifier = mto_details.get("Item Code") or mto_details.get("Description") or f"ID {mto_details['mto_item_id']}"
                    comment_parts.append(f"{item['used_qty']} x {identifier}")

        form_data["Comment"] = " | ".join(comment_parts)

        success, msg = self.main_window.dm.register_miv_record(self.main_window.current_project.id, form_data, consumed_items, spool_items)

        if success:
            self.main_window.log_to_console(msg, "success")
            self.main_window.update_line_dashboard()
            for field in ["MIV Tag", "Location", "Status"]:
                if field in self.main_window.entries:
                    self.main_window.entries[field].clear()
        else:
            self.main_window.log_to_console(msg, "error")

    def handle_search(self):
        search_type = self.main_window.search_type_combo.currentText()

        if search_type == "Line Number":
            if not self.main_window.current_project:
                self.main_window.show_message("خطا", "لطفاً ابتدا یک پروژه را بارگذاری کنید.", "warning")
                return

            line_no = self.main_window.search_entry_line.text().strip().upper()
            if not line_no:
                self.main_window.show_message("خطا", "لطفاً شماره خط را وارد کنید.", "warning")
                return

            self.main_window.entries["Line No"].setText(line_no)
            self.main_window.update_line_dashboard(line_no)

            records = self.main_window.dm.search_miv_by_line_no(self.main_window.current_project.id, line_no)

            if not records:
                self.main_window.show_message("نتیجه", f"هیچ رکوردی برای خط '{line_no}' یافت نشد.", "info")
                return

            self._show_search_results_dialog(records, f"نتایج جستجو - خط {line_no}")

        elif search_type == "MIV Tag":
            tag_query = self.main_window.search_entry_tag.text().strip()
            if not tag_query:
                self.main_window.show_message("خطا", "لطفاً MIV Tag را وارد کنید.", "warning")
                return

            results = self.main_window.dm.search_miv_by_tag(tag_query)
            if not results:
                self.main_window.show_message("نتیجه", f"هیچ رکوردی با تگ '{tag_query}' یافت نشد.", "info")
                return

            self._show_search_results_dialog(results, f"نتایج جستجو - MIV Tag: {tag_query}")

        elif search_type == "Registered For":
            name_query = self.main_window.search_entry_reg_for.text().strip()
            if not name_query:
                self.main_window.show_message("خطا", "لطفاً نام را وارد کنید.", "warning")
                return

            results = self.main_window.dm.search_miv_by_registered_for(name_query)
            if not results:
                self.main_window.show_message("نتیجه", f"هیچ رکوردی برای '{name_query}' یافت نشد.", "info")
                return

            self._show_search_results_dialog(results, f"نتایج جستجو - Registered For: {name_query}")

        elif search_type == "Registered By":
            username_query = self.main_window.search_entry_reg_by.text().strip()
            if not username_query:
                self.main_window.show_message("خطا", "لطفاً نام کاربری را وارد کنید.", "warning")
                return

            results = self.main_window.dm.search_miv_by_registered_by(username_query)
            if not results:
                self.main_window.show_message("نتیجه", f"هیچ رکوردی توسط '{username_query}' یافت نشد.", "info")
                return

            self._show_search_results_dialog(results, f"نتایج جستجو - Registered By: {username_query}")

        elif search_type == "Date Range":
            start_date = self.main_window.search_date_start.date().toString("yyyy-MM-dd")
            end_date = self.main_window.search_date_end.date().toString("yyyy-MM-dd")

            status_text = self.main_window.search_date_status.currentText()
            is_complete = None
            if status_text == "تکمیل شده":
                is_complete = True
            elif status_text == "تکمیل نشده":
                is_complete = False

            results = self.main_window.dm.search_miv_by_date_range(start_date, end_date, is_complete)
            if not results:
                self.main_window.show_message("نتیجه", "هیچ رکوردی در بازه زمانی انتخابی یافت نشد.", "info")
                return

            self._show_search_results_dialog(results, f"نتایج جستجو - Date Range: {start_date} to {end_date}")

        elif search_type == "Completion Status":
            status_text = self.main_window.search_completion_combo.currentText()
            is_complete = (status_text == "تکمیل شده")

            results = self.main_window.dm.search_miv_by_completion_status(is_complete)
            if not results:
                self.main_window.show_message("نتیجه", f"هیچ رکورد {status_text} یافت نشد.", "info")
                return

            self._show_search_results_dialog(results, f"نتایج جستجو - وضعیت: {status_text}")

    def handle_update_dashboard_button_click(self):
        if not self.main_window.current_project:
            self.main_window.show_message("هشدار", "لطفاً ابتدا یک پروژه را انتخاب کنید.", "warning")
            return

        line_no = self.main_window.entries["Line No"].text().strip()
        if not line_no:
            self.main_window.show_message("هشدار", "لطفاً شماره خط را برای نمایش نمودار وارد کنید.", "warning")
            return

        self.main_window.update_line_dashboard(line_no)

    def handle_data_update_from_csv(self):
        from PyQt6.QtWidgets import QInputDialog

        dlg = QInputDialog(self.main_window)
        dlg.setWindowTitle("ورود رمز")
        dlg.setLabelText("این یک عملیات حساس است. لطفاً رمز را وارد کنید:")
        dlg.setTextEchoMode(QLineEdit.EchoMode.Password)
        if not dlg.exec() or dlg.textValue() != self.main_window.dashboard_password:
            self.main_window.show_message("خطا", "رمز اشتباه است یا عملیات لغو شد.", "error")
            return

        confirm = QMessageBox.warning(self.main_window, "تایید عملیات بسیار مهم",
                                      "<b>هشدار!</b>\n\n"
                                      "شما در حال به‌روزرسانی داده‌ها از فایل‌های CSV هستید.\n"
                                      "این عملیات داده‌های موجود در دیتابیس را بر اساس فایل‌های انتخابی <b>جایگزین</b> خواهد کرد.\n\n"
                                      "<b>این عملیات غیرقابل بازگشت است. آیا مطمئن هستید؟</b>",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                                      QMessageBox.StandardButton.Cancel)
        if confirm == QMessageBox.StandardButton.Cancel:
            self.main_window.log_to_console("عملیات به‌روزرسانی داده لغو شد.", "warning")
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self.main_window,
            "فایل‌های CSV مورد نظر را انتخاب کنید (MTO-*.csv, Spools.csv, SpoolItems.csv)",
            "",
            "CSV Files (*.csv)"
        )

        if not file_paths:
            self.main_window.log_to_console("هیچ فایلی انتخاب نشد. عملیات لغو شد.", "warning")
            return

        self.main_window.log_to_console(f"شروع فرآیند به‌روزرسانی برای {len(file_paths)} فایل انتخابی...", "info")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            QApplication.processEvents()

            success, message = self.main_window.dm.process_selected_csv_files(file_paths)

            if success:
                self.main_window.log_to_console(message, "success")
                self.main_window.show_message("موفق", message)
                self.main_window.populate_project_combo()
            else:
                self.main_window.log_to_console(message, "error")
                self.main_window.show_message("خطا", message, "error")
        finally:
            QApplication.restoreOverrideCursor()

    def handle_iso_search(self):
        raw_line = (self.main_window.entries.get("Line No").text() if self.main_window.entries.get("Line No") else "").strip()
        if not raw_line:
            self.main_window.log_to_console("⚠️ لطفاً ابتدا Line No را وارد کنید.", level="warning")
            return

        dialog = IsoSearchDialog(self.main_window.dm, raw_line, parent=self.main_window)

        dialog.files_opened.connect(lambda paths:
                                    self.main_window.log_to_console(f"✅ {len(paths)} فایل از دیالوگ باز شد", "success")
                                    )

        dialog.exec()

    def handle_report_export(self, report_type: str):
        if not self.main_window.current_project and report_type not in ['spool_inventory', 'spool_consumption']:
            self.main_window.show_message("Warning", "Please select a project for this report first.", "warning")
            return

        report_map = {
            'mto_summary': ("MTO Summary", self.main_window.dm.get_project_mto_summary),
            'line_status': ("Line Status List", self.main_window.dm.get_project_line_status_list),
            'shortage': ("Shortage Report", self.main_window.dm.get_shortage_report),
            'spool_inventory': ("Spool Inventory", self.main_window.dm.get_spool_inventory_report),
            'spool_consumption': ("Spool Consumption History", self.main_window.dm.get_spool_consumption_history)
        }
        report_name, data_func = report_map[report_type]
        project_name = self.main_window.current_project.name if self.main_window.current_project else "Global"
        default_filename = f"{report_name.replace(' ', '_')}_{project_name}.xlsx"

        path, _ = QFileDialog.getSaveFileName(
            self.main_window, f"Save {report_name} Report", default_filename, "Excel Files (*.xlsx);;PDF Files (*.pdf)")

        if not path:
            return

        self.main_window.log_to_console(f"Preparing '{report_name}' report...", "info")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            report_data = []
            if report_type in ['mto_summary', 'line_status', 'shortage']:
                raw_output = data_func(self.main_window.current_project.id)
            else:
                raw_output = data_func()

            if isinstance(raw_output, dict) and 'data' in raw_output:
                report_data = raw_output['data']
            elif isinstance(raw_output, list):
                report_data = raw_output

            success, msg = self.main_window.dm.export_data_to_file(report_data, path, report_name)

            if success:
                self.main_window.show_message("Success", msg)
            else:
                self.main_window.show_message("Error", msg, "error")

        except Exception as e:
            self.main_window.show_message("Critical Error", f"An unexpected error occurred during report generation: {e}", "error")
        finally:
            QApplication.restoreOverrideCursor()

    def handle_line_status_export(self):
        if not self.main_window.current_project:
            self.main_window.show_message("هشدار", "لطفاً ابتدا یک پروژه را بارگذاری کنید.", "warning")
            return

        line_no = self.main_window.entries["Line No"].text().strip().upper()
        if not line_no:
            self.main_window.show_message("هشدار", "لطفاً شماره خط مورد نظر را در فیلد Line No وارد کنید.", "warning")
            return

        project_name = self.main_window.current_project.name.replace(" ", "_")
        line_name = line_no.replace("\"", "")
        default_filename = f"Line_Status_{project_name}_{line_name}.xlsx"

        path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            f"ذخیره گزارش وضعیت خط: {line_no}",
            default_filename,
            "Excel Files (*.xlsx);;PDF Files (*.pdf)"
        )

        if not path:
            self.main_window.log_to_console(f"عملیات خروجی برای خط '{line_no}' لغو شد.", "warning")
            return

        self.main_window.log_to_console(f"در حال آماده‌سازی گزارش برای خط '{line_no}'...", "info")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            success, msg = self.main_window.dm.export_detailed_line_report_to_file(
                self.main_window.current_project.id, line_no, path
            )

            self.main_window.show_message("نتیجه عملیات", msg, "info" if success else "error")
            self.main_window.log_to_console(msg, "success" if success else "error")

        except Exception as e:
            error_msg = f"خطای پیش‌بینی نشده در تولید گزارش خط: {e}"
            self.main_window.show_message("خطای بحرانی", error_msg, "error")
            self.main_window.log_to_console(error_msg, "error")
        finally:
            QApplication.restoreOverrideCursor()

    def on_text_changed(self):
        self.main_window.suggestion_timer.start()

    def fetch_suggestions(self):
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, QLineEdit):
            text = focused_widget.text()
        else:
            return

        if len(text) < 2:
            self.main_window.line_completer_model.setStringList([])
            return

        self.main_window.suggestion_data = self.main_window.dm.get_line_no_suggestions(text)

        display_list = [item['display'] for item in self.main_window.suggestion_data]
        self.main_window.line_completer_model.setStringList(display_list)

    def on_suggestion_selected(self, selected_display_text, target_widget):
        selected_item = next((item for item in self.main_window.suggestion_data if item['display'] == selected_display_text), None)

        if not selected_item:
            return

        project_name = selected_item['project_name']
        line_no = selected_item['line_no']

        index = self.main_window.project_combo.findText(project_name, Qt.MatchFlag.MatchFixedString)
        if index >= 0:
            self.main_window.project_combo.setCurrentIndex(index)
            self.main_window.load_project()

        if target_widget:
            target_widget.blockSignals(True)
            target_widget.setText(line_no)
            target_widget.blockSignals(False)

        if self.main_window.current_project:
            self.main_window.update_line_dashboard(line_no)

    def _show_search_results_dialog(self, records, title):
        if records and isinstance(records[0], dict):
            records = [self._dict_to_record_format(r) for r in records]

        self.main_window.log_to_console(f"{len(records)} رکورد یافت شد.", "info")

        dlg = QDialog(self.main_window)
        dlg.setWindowTitle(title)
        dlg.resize(1200, 500)
        layout = QVBoxLayout(dlg)

        table = QTableWidget()
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels([
            "ID", "Project", "Line No", "MIV Tag", "Location", "Status",
            "Registered For", "Registered By", "Last Updated", "Actions"
        ])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.setRowCount(len(records))

        for row, rec in enumerate(records):
            table.setItem(row, 0, QTableWidgetItem(str(rec.id)))
            table.setItem(row, 1, QTableWidgetItem(rec.project_name if hasattr(rec, 'project_name') else "N/A"))
            table.setItem(row, 2, QTableWidgetItem(rec.line_no or ""))
            table.setItem(row, 3, QTableWidgetItem(rec.miv_tag or ""))
            table.setItem(row, 4, QTableWidgetItem(rec.location or ""))
            table.setItem(row, 5, QTableWidgetItem(rec.status or ""))
            table.setItem(row, 6, QTableWidgetItem(rec.registered_for or ""))
            table.setItem(row, 7, QTableWidgetItem(rec.registered_by or ""))
            table.setItem(row, 8,
                          QTableWidgetItem(rec.last_updated.strftime('%Y-%m-%d %H:%M') if rec.last_updated else ""))

            # دکمه‌های عملیات
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)

            view_btn = QPushButton("📊")
            view_btn.setToolTip("مشاهده جزئیات")
            view_btn.clicked.connect(partial(self._show_miv_details, rec.id))

            edit_btn = QPushButton("⚙️")
            edit_btn.setToolTip("ویرایش/حذف")
            edit_btn.clicked.connect(partial(self._show_miv_actions, rec, dlg))

            actions_layout.addWidget(view_btn)
            actions_layout.addWidget(edit_btn)
            table.setCellWidget(row, 9, actions_widget)

        layout.addWidget(table)

        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(dlg.close)
        layout.addWidget(close_btn)

        dlg.exec()

    def _show_miv_details(self, miv_record_id):
        try:
            details = self.main_window.dm.get_miv_consumption_details(miv_record_id)

            if not details:
                self.main_window.show_message("خطا", "جزئیات این رکورد یافت نشد.", "warning")
                return

            dlg = QDialog(self.main_window)
            dlg.setWindowTitle(f"جزئیات مصرف - MIV ID: {miv_record_id}")
            dlg.resize(1000, 600)
            layout = QVBoxLayout(dlg)

            tabs = QTabWidget()

            # تب مصرف MTO
            mto_tab = QWidget()
            mto_layout = QVBoxLayout(mto_tab)

            mto_data = details.get('mto_consumptions', [])
            if mto_data:
                mto_table = QTableWidget()
                mto_table.setColumnCount(5)
                mto_table.setHorizontalHeaderLabels([
                    "Item Code", "Description", "Unit", "Used Qty", "Timestamp"
                ])
                mto_table.setRowCount(len(mto_data))
                mto_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

                for row, item in enumerate(mto_data):
                    mto_table.setItem(row, 0, QTableWidgetItem(item.get('item_code', 'N/A')))
                    mto_table.setItem(row, 1, QTableWidgetItem(item.get('description', 'N/A')))
                    mto_table.setItem(row, 2, QTableWidgetItem(item.get('unit', 'N/A')))
                    mto_table.setItem(row, 3, QTableWidgetItem(str(item.get('used_qty', 0))))
                    mto_table.setItem(row, 4, QTableWidgetItem(
                        item.get('timestamp', '').strftime('%Y-%m-%d %H:%M') if item.get('timestamp') else 'N/A'
                    ))

                mto_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                mto_layout.addWidget(mto_table)
            else:
                mto_layout.addWidget(QLabel("هیچ مصرف مستقیم MTO ثبت نشده است."))

            tabs.addTab(mto_tab, "مصرف MTO")

            # تب مصرف اسپول
            spool_tab = QWidget()
            spool_layout = QVBoxLayout(spool_tab)

            spool_data = details.get('spool_consumptions', [])
            if spool_data:
                spool_table = QTableWidget()
                spool_table.setColumnCount(6)
                spool_table.setHorizontalHeaderLabels([
                    "Spool ID", "Component Type", "Item Code", "Used Qty", "Unit", "Timestamp"
                ])
                spool_table.setRowCount(len(spool_data))
                spool_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

                for row, item in enumerate(spool_data):
                    spool_table.setItem(row, 0, QTableWidgetItem(item.get('spool_id', 'N/A')))
                    spool_table.setItem(row, 1, QTableWidgetItem(item.get('component_type', 'N/A')))
                    spool_table.setItem(row, 2, QTableWidgetItem(item.get('item_code', 'N/A')))
                    spool_table.setItem(row, 3, QTableWidgetItem(str(item.get('used_qty', 0))))
                    spool_table.setItem(row, 4, QTableWidgetItem(item.get('unit', 'N/A')))
                    spool_table.setItem(row, 5, QTableWidgetItem(
                        item.get('timestamp', '').strftime('%Y-%m-%d %H:%M') if item.get('timestamp') else 'N/A'
                    ))

                spool_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                spool_layout.addWidget(spool_table)
            else:
                spool_layout.addWidget(QLabel("هیچ مصرف اسپول ثبت نشده است."))

            tabs.addTab(spool_tab, "مصرف اسپول")

            layout.addWidget(tabs)

            close_btn = QPushButton("بستن")
            close_btn.clicked.connect(dlg.close)
            layout.addWidget(close_btn)

            dlg.exec()

        except Exception as e:
            self.main_window.show_message("خطا", f"خطا در نمایش جزئیات: {e}", "error")
            import traceback
            self.main_window.log_to_console(traceback.format_exc(), "error")

    def _show_miv_actions(self, record, parent_dialog):
        try:
            record_id = record.id if hasattr(record, 'id') else record['id']
        except:
            self.main_window.show_message("خطا", "شناسه رکورد قابل دسترسی نیست.", "error")
            return

        session = self.main_window.dm.get_session()
        try:
            full_record = session.get(MIVRecord, record_id)
            if not full_record:
                self.main_window.show_message("خطا", "رکورد در دیتابیس یافت نشد.", "error")
                return
        finally:
            session.close()

        menu = QMenu(self.main_window)

        edit_action = menu.addAction("✏️ ویرایش رکورد")
        edit_items_action = menu.addAction("⚙️ ویرایش آیتم‌های مصرفی")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ حذف رکورد")

        action = menu.exec(QCursor.pos())

        if action == edit_action:
            edit_dialog = QDialog(self.main_window)
            edit_dialog.setWindowTitle(f"ویرایش رکورد: {full_record.miv_tag}")
            edit_dialog.setMinimumWidth(400)

            form_layout = QFormLayout(edit_dialog)

            location_input = QLineEdit(full_record.location or "")
            location_input.setPlaceholderText("مکان را وارد کنید...")

            status_input = QLineEdit(full_record.status or "")
            status_input.setPlaceholderText("وضعیت را وارد کنید...")

            comment_input = QLineEdit(full_record.comment or "")
            comment_input.setPlaceholderText("توضیحات (اختیاری)...")

            registered_for_input = QLineEdit(full_record.registered_for or "")
            registered_for_input.setPlaceholderText("ثبت شدهرای...")

            form_layout.addRow("Location:", location_input)

            form_layout.addRow("Status:", status_input)
            form_layout.addRow("Comment:", comment_input)
            form_layout.addRow("Registered For:", registered_for_input)

            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(edit_dialog.accept)
            buttons.rejected.connect(edit_dialog.reject)
            form_layout.addWidget(buttons)

            if edit_dialog.exec() == QDialog.DialogCode.Accepted:
                updated_data = {
                    "location": location_input.text().strip(),
                    "status": status_input.text().strip(),
                    "comment": comment_input.text().strip(),
                    "registered_for": registered_for_input.text().strip()
                }

                success, msg = self.main_window.dm.update_miv_record(
                    record_id,
                    updated_data,
                    user=self.main_window.current_user
                )
                self.main_window.show_message("نتیجه", msg, "success" if success else "error")

                if success:
                    parent_dialog.close()
                    self.main_window.update_line_dashboard()

        elif action == edit_items_action:
            dialog = MTOConsumptionDialog(
                self.main_window.dm,
                full_record.project_id,
                full_record.line_no,
                miv_record_id=record_id,
                parent=self.main_window
            )

            if dialog.exec():
                consumed_items, spool_items = dialog.get_data()
                success, msg = self.main_window.dm.update_miv_items(
                    record_id,
                    consumed_items,
                    spool_items,
                    user=self.main_window.current_user
                )
                self.main_window.show_message("نتیجه", msg, "success" if success else "error")

                if success:
                    parent_dialog.close()
                    self.main_window.update_line_dashboard()

        elif action == delete_action:
            confirm = QMessageBox.question(
                self.main_window,
                "تأیید حذف",
                f"آیا از حذف رکورد با تگ '{full_record.miv_tag}' مطمئن هستید؟\n"
                "این عملیات غیرقابل بازگشت است!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if confirm == QMessageBox.StandardButton.Yes:
                success, msg = self.main_window.dm.delete_miv_record(record_id, user=self.main_window.current_user)
                self.main_window.show_message("نتیجه", msg, "success" if success else "error")

                if success:
                    parent_dialog.close()
                    self.main_window.update_line_dashboard()

    def _dict_to_record_format(self, data_dict):
        """
        دیکشنری را به فرمت شیء تبدیل می‌کند (Proxy Object).
        """
        class RecordProxy:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)

        return RecordProxy(data_dict)
