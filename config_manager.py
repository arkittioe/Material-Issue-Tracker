# file: config_manager.py

import configparser
import os
import sys

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ایجاد نمونه ConfigParser
config = configparser.ConfigParser()

# ✅ استفاده از resource_path
config_path = resource_path('config.ini')

# خواندن فایل کانفیگ
if os.path.exists(config_path):
    config.read(config_path, encoding='utf-8')
else:
    print(f"⚠️ Warning: config.ini not found at {config_path}")

# --- استخراج مقادیر PostgreSQL ---
DB_HOST = config.get('PostgreSQL', 'host', fallback='localhost').strip()
DB_PORT = config.getint('PostgreSQL', 'port', fallback=5432)
DB_NAME = config.get('PostgreSQL', 'dbname', fallback='miv_db').strip()
DB_USER = config.get('PostgreSQL', 'user', fallback='').strip()
DB_PASSWORD = config.get('PostgreSQL', 'password', fallback='').strip()

# --- استخراج بقیه مقادیر ---
ISO_PATH = config.get('Paths', 'iso_drawing_path', fallback=r'\\fs\Piping\Piping\ISO').strip()
DASHBOARD_PASSWORD = config.get('Security', 'dashboard_password', fallback='default_password').strip()
