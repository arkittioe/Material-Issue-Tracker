# iso_event_handler.py

import os
import time
from collections import defaultdict
from threading import Timer, Lock
from typing import Set, Dict, Optional
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal
from watchdog.events import FileSystemEventHandler


class IsoIndexEventHandler(QObject, FileSystemEventHandler):
    """
    کلاس پیشرفته برای مدیریت تغییرات فایل‌های ISO/DWG با قابلیت‌های زیر:
    - Event Debouncing برای جلوگیری از پردازش مکرر
    - Batch Processing برای بهینه‌سازی عملکرد
    - مدیریت خطای پیشرفته با Retry Logic
    - آمارگیری و گزارش‌دهی کامل
    """

    # سیگنال‌های PyQt برای ارتباط با UI
    status_updated = pyqtSignal(str, str)  # (message, level)
    progress_updated = pyqtSignal(int, str)  # (percentage, text)
    file_processed = pyqtSignal(str, str)  # (file_path, action_type)
    batch_completed = pyqtSignal(int)  # (files_count)
    error_occurred = pyqtSignal(str, str)  # (file_path, error_message)

    # تنظیمات پیش‌فرض
    SUPPORTED_EXTENSIONS = {".pdf", ".dwg"}
    DEBOUNCE_DELAY = 1.0  # ثانیه تاخیر برای debouncing
    BATCH_SIZE = 50  # تعداد فایل در هر batch
    BATCH_DELAY = 2.0  # ثانیه تاخیر برای جمع‌آوری batch
    MAX_RETRY_ATTEMPTS = 3  # تعداد تلاش مجدد در صورت خطا
    RETRY_DELAY = 0.5  # ثانیه تاخیر بین تلاش‌های مجدد

    def __init__(self, dm, config: Optional[Dict] = None):
        """
        Args:
            dm: شیء DataManager برای عملیات دیتابیس
            config: دیکشنری تنظیمات اختیاری برای سفارشی‌سازی
        """
        super().__init__()

        self.dm = dm
        self._lock = Lock()  # برای thread-safety

        # اعمال تنظیمات سفارشی (در صورت وجود)
        if config:
            self.SUPPORTED_EXTENSIONS = config.get('extensions', self.SUPPORTED_EXTENSIONS)
            self.DEBOUNCE_DELAY = config.get('debounce_delay', self.DEBOUNCE_DELAY)
            self.BATCH_SIZE = config.get('batch_size', self.BATCH_SIZE)
            self.BATCH_DELAY = config.get('batch_delay', self.BATCH_DELAY)
            self.MAX_RETRY_ATTEMPTS = config.get('max_retries', self.MAX_RETRY_ATTEMPTS)

        # ساختارهای داده برای مدیریت رویدادها
        self._pending_events: Dict[str, Dict] = {}  # {file_path: {'action': str, 'timer': Timer}}
        self._batch_queue: Set[str] = set()  # صف پردازش دسته‌ای
        self._batch_timer: Optional[Timer] = None

        # آمار عملکرد
        self.stats = {
            'created': 0,
            'modified': 0,
            'deleted': 0,
            'moved': 0,
            'errors': 0,
            'total_processed': 0,
            'last_batch_time': None,
            'start_time': datetime.now()
        }

        self.status_updated.emit("ISO Event Handler initialized successfully", "success")

    def _is_supported(self, path: str) -> bool:
        """بررسی اینکه آیا فایل از فرمت‌های پشتیبانی شده است یا خیر"""
        if not path:
            return False
        extension = os.path.splitext(path)[1].lower()
        return extension in self.SUPPORTED_EXTENSIONS

    def _debounce_event(self, file_path: str, action: str, callback):
        """
        پیاده‌سازی Debouncing برای جلوگیری از پردازش مکرر رویدادها

        Args:
            file_path: مسیر فایل
            action: نوع عملیات (created, modified, deleted, moved)
            callback: تابع callback برای اجرای عملیات واقعی
        """
        with self._lock:
            # لغو تایمر قبلی برای این فایل (در صورت وجود)
            if file_path in self._pending_events:
                old_timer = self._pending_events[file_path].get('timer')
                if old_timer and old_timer.is_alive():
                    old_timer.cancel()

            # ساخت تایمر جدید
            timer = Timer(self.DEBOUNCE_DELAY, callback)
            self._pending_events[file_path] = {
                'action': action,
                'timer': timer,
                'timestamp': time.time()
            }
            timer.start()

    def _process_with_retry(self, operation, file_path: str, max_attempts: int = None):
        """
        اجرای عملیات با قابلیت retry در صورت بروز خطا

        Args:
            operation: تابع عملیاتی که باید اجرا شود
            file_path: مسیر فایل
            max_attempts: حداکثر تعداد تلاش (پیش‌فرض از تنظیمات کلاس)

        Returns:
            bool: True در صورت موفقیت، False در صورت شکست
        """
        if max_attempts is None:
            max_attempts = self.MAX_RETRY_ATTEMPTS

        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                operation(file_path)
                return True

            except FileNotFoundError:
                # فایل حذف شده، نیازی به retry نیست
                return False

            except PermissionError as e:
                last_error = f"Permission denied: {e}"
                if attempt < max_attempts:
                    time.sleep(self.RETRY_DELAY * attempt)  # تاخیر افزایشی

            except Exception as e:
                last_error = f"Unexpected error: {e}"
                if attempt < max_attempts:
                    time.sleep(self.RETRY_DELAY * attempt)

        # در صورت شکست تمام تلاش‌ها
        self.stats['errors'] += 1
        self.error_occurred.emit(file_path, last_error or "Unknown error")
        self.status_updated.emit(
            f"Failed to process '{os.path.basename(file_path)}' after {max_attempts} attempts",
            "error"
        )
        return False

    def _add_to_batch(self, file_path: str):
        """افزودن فایل به صف پردازش دسته‌ای"""
        with self._lock:
            self._batch_queue.add(file_path)

            # اگر صف پر شد، بلافاصله پردازش کن
            if len(self._batch_queue) >= self.BATCH_SIZE:
                if self._batch_timer and self._batch_timer.is_alive():
                    self._batch_timer.cancel()
                self._process_batch()

            # در غیر این صورت، تایمر را ریست کن
            elif not self._batch_timer or not self._batch_timer.is_alive():
                self._batch_timer = Timer(self.BATCH_DELAY, self._process_batch)
                self._batch_timer.start()

    def _process_batch(self):
        """پردازش دسته‌ای فایل‌های موجود در صف"""
        with self._lock:
            if not self._batch_queue:
                return

            files_to_process = list(self._batch_queue)
            self._batch_queue.clear()
            self._batch_timer = None

        # پردازش فایل‌ها به صورت دسته‌ای
        total_files = len(files_to_process)
        self.status_updated.emit(f"Processing batch of {total_files} files...", "info")

        success_count = 0
        for idx, file_path in enumerate(files_to_process, 1):
            if self._process_with_retry(self.dm.upsert_iso_index_entry, file_path):
                success_count += 1
                self.stats['total_processed'] += 1

            # ارسال پیشرفت
            progress = int((idx / total_files) * 100)
            self.progress_updated.emit(progress, "Batch Processing")

        # ثبت زمان اتمام batch
        self.stats['last_batch_time'] = datetime.now()

        # ارسال سیگنال اتمام batch
        self.batch_completed.emit(success_count)
        self.status_updated.emit(
            f"Batch completed: {success_count}/{total_files} files processed successfully",
            "success" if success_count == total_files else "warning"
        )

    # ===== رویدادهای FileSystemEventHandler =====

    def on_created(self, event):
        """رویداد ایجاد فایل جدید"""
        if event.is_directory or not self._is_supported(event.src_path):
            return

        def process():
            if self._process_with_retry(self.dm.upsert_iso_index_entry, event.src_path):
                self.stats['created'] += 1
                self.stats['total_processed'] += 1
                self.file_processed.emit(event.src_path, "created")
                print(f"✅ File created and indexed: {event.src_path}")

        self._debounce_event(event.src_path, 'created', process)

    def on_deleted(self, event):
        """رویداد حذف فایل"""
        if event.is_directory or not self._is_supported(event.src_path):
            return

        def process():
            if self._process_with_retry(self.dm.remove_iso_index_entry, event.src_path):
                self.stats['deleted'] += 1
                self.stats['total_processed'] += 1
                self.file_processed.emit(event.src_path, "deleted")
                print(f"🗑️ File deleted and removed from index: {event.src_path}")

        self._debounce_event(event.src_path, 'deleted', process)

    def on_modified(self, event):
        """رویداد تغییر فایل"""
        if event.is_directory or not self._is_supported(event.src_path):
            return

        def process():
            if self._process_with_retry(self.dm.upsert_iso_index_entry, event.src_path):
                self.stats['modified'] += 1
                self.stats['total_processed'] += 1
                self.file_processed.emit(event.src_path, "modified")
                print(f"📝 File modified and re-indexed: {event.src_path}")

        self._debounce_event(event.src_path, 'modified', process)

    def on_moved(self, event):
        """رویداد انتقال/تغییر نام فایل"""
        if event.is_directory:
            return

        src_supported = self._is_supported(event.src_path)
        dest_supported = self._is_supported(event.dest_path)

        if not src_supported and not dest_supported:
            return

        def process():
            # حذف مسیر قدیمی (اگر پشتیبانی می‌شد)
            if src_supported:
                self._process_with_retry(self.dm.remove_iso_index_entry, event.src_path)

            # افزودن مسیر جدید (اگر پشتیبانی می‌شود)
            if dest_supported:
                if self._process_with_retry(self.dm.upsert_iso_index_entry, event.dest_path):
                    self.stats['moved'] += 1
                    self.stats['total_processed'] += 1
                    self.file_processed.emit(event.dest_path, "moved")
                    print(f"📦 File moved: {event.src_path} → {event.dest_path}")

        self._debounce_event(event.dest_path, 'moved', process)

    # ===== متدهای کمکی و گزارش‌دهی =====

    def get_statistics(self) -> Dict:
        """
        دریافت آمار کامل عملکرد handler

        Returns:
            دیکشنری حاوی آمار کامل
        """
        uptime = (datetime.now() - self.stats['start_time']).total_seconds()

        return {
            **self.stats,
            'uptime_seconds': uptime,
            'files_per_minute': (self.stats['total_processed'] / uptime * 60) if uptime > 0 else 0,
            'pending_events': len(self._pending_events),
            'batch_queue_size': len(self._batch_queue),
            'error_rate': (self.stats['errors'] / self.stats['total_processed'] * 100)
            if self.stats['total_processed'] > 0 else 0
        }

    def reset_statistics(self):
        """بازنشانی آمار"""
        with self._lock:
            self.stats = {
                'created': 0,
                'modified': 0,
                'deleted': 0,
                'moved': 0,
                'errors': 0,
                'total_processed': 0,
                'last_batch_time': None,
                'start_time': datetime.now()
            }
        self.status_updated.emit("Statistics reset", "info")

    def flush_pending_events(self):
        """
        اجبار پردازش فوری تمام رویدادهای معلق
        (مفید برای زمان خاموش شدن برنامه)
        """
        with self._lock:
            # لغو تمام تایمرها و اجرای فوری callback ها
            for file_path, event_data in list(self._pending_events.items()):
                timer = event_data.get('timer')
                if timer and timer.is_alive():
                    timer.cancel()
                    # اینجا می‌توانید callback را مستقیماً فراخوانی کنید

            self._pending_events.clear()

            # پردازش batch معلق
            if self._batch_timer and self._batch_timer.is_alive():
                self._batch_timer.cancel()

            if self._batch_queue:
                self._process_batch()

    def cleanup(self):
        """
        پاکسازی و آزادسازی منابع
        باید قبل از بستن برنامه فراخوانی شود
        """
        self.flush_pending_events()
        self.status_updated.emit("ISO Event Handler cleaned up", "info")

    def __del__(self):
        """Destructor برای اطمینان از پاکسازی منابع"""
        try:
            self.cleanup()
        except:
            pass
