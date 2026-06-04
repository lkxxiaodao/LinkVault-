import os

APP_NAME = "LinkVault"

DATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), APP_NAME)
DB_PATH = os.path.join(DATA_DIR, 'linkvault.db')
FAVICON_DIR = os.path.join(DATA_DIR, 'favicons')

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