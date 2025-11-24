# splash_screen.py

import os
from PyQt6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QProgressBar
from PyQt6.QtGui import QPixmap, QMovie, QColor
from PyQt6.QtCore import Qt, QTimer


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    import sys
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class SplashScreen(QSplashScreen):
    def __init__(self):
        logo_path = resource_path('splash_logo.gif')

        # پس‌زمینه اولیه
        splash_pix = QPixmap(logo_path) if os.path.exists(logo_path) else QPixmap()
        super().__init__(splash_pix, Qt.WindowType.WindowStaysOnTopHint)

        # لایه اصلی
        layout = QVBoxLayout(self)

        # QLabel برای نمایش GIF
        self.gif_label = QLabel(self)
        self.gif_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.gif_label)

        # QLabel برای نمایش پیام
        self.message_label = QLabel(self)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet("color: white; font-size: 16px; margin-bottom: 20px;")
        layout.addWidget(self.message_label)

        # اگر GIF وجود دارد → روی QLabel بگذاریم
        if os.path.exists(logo_path):
            self.movie = QMovie(logo_path)
            if self.movie.isValid():
                self.gif_label.setMovie(self.movie)
                self.movie.start()

        # اگر تصویر پیدا نشد → پس‌زمینه خالی بده
        if splash_pix.isNull():
            self.setStyleSheet("background-color: #333;")

        # پیام اولیه
        self.showMessage("در حال بارگذاری...", QColor(Qt.GlobalColor.white))

        self.show()

    def showMessage(self, message, color):
        """متد سفارشی برای نمایش پیام با رنگ مشخص."""
        self.message_label.setText(message)
        self.message_label.setStyleSheet(f"color: {color.name()}; font-size: 16px; margin-bottom: 20px;")
