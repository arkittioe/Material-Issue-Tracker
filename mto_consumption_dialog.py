# mto_consumption_dialog.py

from functools import partial
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialogButtonBox, QDoubleSpinBox, QPushButton
)
from PyQt6.QtCore import Qt
from models import SpoolItem
from data_manager import DataManager
from spool_selection_dialog import SpoolSelectionDialog


class MTOConsumptionDialog(QDialog):
    def __init__(self, dm: DataManager, project_id: int, line_no: str, miv_record_id: int = None, parent=None):
        super().__init__(parent)
        self.dm = dm
        self.project_id = project_id
        self.line_no = line_no
        self.miv_record_id = miv_record_id

        # Data storage
        self.consumed_data = []  # For direct MTO consumption
        self.spool_consumption_data = []  # For spool consumption
        self.spool_selections = {}  # Internal UI mapping: {row_index: [list of spool selections]}

        self.existing_consumptions = {}

        self.setWindowTitle(f"مدیریت مصرف برای خط: {self.line_no}")
        self.setMinimumSize(1200, 600)

        if self.miv_record_id:
            self.setWindowTitle(f"ویرایش آیتم‌های MIV ID: {self.miv_record_id}")
            self.existing_consumptions = self.dm.get_consumptions_for_miv(self.miv_record_id)

        layout = QVBoxLayout(self)
        info_label = QLabel(
            "مقدار مصرف مستقیم را وارد کنید یا از دکمه 'انتخاب اسپول' برای برداشت از انبار اسپول استفاده نمایید.")
        layout.addWidget(info_label)

        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            # MTO Info
            "Item Code", "Description", "Total Qty", "Used (All)", "Remaining", "Unit",
            # New MTO Details
            "Bore", "Type",
            # Consumption for this MIV
            "مصرف مستقیم",
            # Spool Info
            "انتخاب اسپول", "Spool ID", "Qty from Spool", "Spool Remaining"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)

        self.populate_table()

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept_data)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def populate_table(self):
        self.progress_data = self.dm.get_enriched_line_progress(self.project_id, self.line_no, readonly=False)
        self.table.setRowCount(len(self.progress_data))

        for row_idx, item in enumerate(self.progress_data):
            mto_item_id = item["mto_item_id"]

            # ستون‌های MTO (0-7)
            self.table.setItem(row_idx, 0, QTableWidgetItem(item["Item Code"] or ""))
            self.table.setItem(row_idx, 1, QTableWidgetItem(item["Description"] or ""))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(item["Total Qty"])))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(item["Used Qty"])))
            remaining_qty = item["Remaining Qty"] or 0
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(remaining_qty)))
            self.table.setItem(row_idx, 5, QTableWidgetItem(item["Unit"] or ""))
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(item.get("Bore") or "")))
            self.table.setItem(row_idx, 7, QTableWidgetItem(item.get("Type") or ""))

            # مصرف موجود در این MIV
            current_miv_total_usage = self.existing_consumptions.get(mto_item_id, 0)

            # SpinBox برای مصرف مستقیم
            spin_box = QDoubleSpinBox()
            max_val = remaining_qty + current_miv_total_usage
            spin_box.setRange(0, max_val)
            spin_box.setDecimals(2)
            spin_box.setValue(current_miv_total_usage)
            self.table.setCellWidget(row_idx, 8, spin_box)

            # دکمه انتخاب اسپول
            spool_btn = QPushButton("انتخاب...")

            # بررسی سازگاری آیتم با انبار اسپول
            item_type = item.get("Type")
            p1_bore = item.get("Bore")
            matching_items = self.dm.get_mapped_spool_items(item_type, p1_bore)

            if not matching_items:  # اگر هیچ اسپولی پیدا نشد
                spool_btn.setEnabled(False)
                spool_btn.setToolTip("هیچ آیتم سازگاری در انبار اسپول یافت نشد.")

            spool_btn.clicked.connect(partial(self.handle_spool_selection, row_idx))
            self.table.setCellWidget(row_idx, 9, spool_btn)

            # ستون‌های اطلاعات اسپول
            for col in [10, 11, 12]:
                self.table.setItem(row_idx, col, QTableWidgetItem(""))

            # اگر کلا آیتمی باقی نمانده، همه کنترل‌ها غیرفعال شوند
            if max_val <= 0:
                spin_box.setEnabled(False)
                spool_btn.setEnabled(False)

            # ستون‌های اطلاعاتی فقط-خواندنی
            for col in list(range(8)) + [10, 11, 12]:
                item_widget = self.table.item(row_idx, col)
                if item_widget:
                    item_widget.setFlags(item_widget.flags() & ~Qt.ItemFlag.ItemIsEditable)

        self.table.resizeColumnsToContents()

    def handle_spool_selection(self, row_idx):
        item_data = self.progress_data[row_idx]
        item_type = item_data.get("Type")
        p1_bore = item_data.get("Bore")

        # Get the remaining quantity for the MTO item
        remaining_qty = item_data.get("Remaining Qty", 0)

        if not item_type:
            self.parent().show_message("هشدار", "نوع آیتم (Type) برای این ردیف MTO مشخص نشده است.", "warning")
            return

        matching_items = self.dm.get_mapped_spool_items(item_type, p1_bore)

        if not matching_items:
            self.parent().show_message(
                "اطلاعات",
                f"هیچ اسپول سازگار برای نوع '{item_type}' و سایز '{p1_bore}' یافت نشد.",
                "info"
            )
            return

        # Pass the remaining_qty to the dialog
        dialog = SpoolSelectionDialog(matching_items, remaining_qty, self)
        if dialog.exec():
            selected_spools = dialog.get_selected_data()
            self.spool_selections[row_idx] = selected_spools
            self.update_row_after_spool_selection(row_idx)

    def update_row_after_spool_selection(self, row_idx):
        selections = self.spool_selections.get(row_idx, [])
        if not selections:
            self.table.item(row_idx, 10).setText("")
            self.table.item(row_idx, 11).setText("")
            self.table.item(row_idx, 12).setText("")
            return

        total_spool_qty = sum(s['used_qty'] for s in selections)

        session = self.dm.get_session()
        try:
            first_selection = selections[0]
            spool_item = session.get(SpoolItem, first_selection['spool_item_id'])
            spool_id_text = str(spool_item.spool.spool_id)
            if len(selections) > 1:
                spool_id_text += f" (+{len(selections) - 1} more)"

            self.table.item(row_idx, 10).setText(spool_id_text)  # Spool ID
            self.table.item(row_idx, 11).setText(str(total_spool_qty))  # Qty from Spool
            self.table.item(row_idx, 12).setText(str(spool_item.qty_available - first_selection['used_qty']))
        finally:
            session.close()

        item_data = self.progress_data[row_idx]
        remaining_qty = item_data["Remaining Qty"] or 0
        current_miv_usage = self.existing_consumptions.get(item_data["mto_item_id"], 0)

        spin_box = self.table.cellWidget(row_idx, 8)
        new_max = (remaining_qty + current_miv_usage) - total_spool_qty
        spin_box.setRange(0, max(0, new_max))
        if spin_box.value() > new_max:
            spin_box.setValue(max(0, new_max))

    def accept_data(self):
        self.consumed_data = []
        self.spool_consumption_data = []

        for row in range(self.table.rowCount()):
            mto_item_id = self.progress_data[row]["mto_item_id"]

            # مصرف مستقیم
            spin_box = self.table.cellWidget(row, 8)
            direct_qty = spin_box.value() if spin_box else 0
            if direct_qty > 0.001:
                self.consumed_data.append({
                    "mto_item_id": mto_item_id,
                    "used_qty": round(direct_qty, 2)
                })

            # مصرف اسپول
            if row in self.spool_selections:
                for sel in self.spool_selections[row]:
                    self.spool_consumption_data.append({
                        "spool_item_id": sel["spool_item_id"],
                        "used_qty": sel["used_qty"]
                    })

        self.accept()

    def get_data(self):
        return self.consumed_data, self.spool_consumption_data
