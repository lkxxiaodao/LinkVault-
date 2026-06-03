import os
import sys

APP_NAME = "LinkVault"
APP_VERSION = "1.0.0"

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), APP_NAME)
DB_PATH = os.path.join(DATA_DIR, 'linkvault.db')
LOG_PATH = os.path.join(DATA_DIR, 'linkvault.log')
FAVICON_DIR = os.path.join(DATA_DIR, 'favicons')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

DB_VERSION = 1

DEFAULT_SETTINGS = {
    'habit_analysis_enabled': '1',
    'first_run_completed': '0',
    'minimize_to_tray': '1',
    'auto_start': '0',
}

HABIT_ANALYSIS_DAYS = 30
HABIT_CONSECUTIVE_DAYS = 3
HABIT_TIME_SLOT_HOURS = 2