import sqlite3
import os
from infra.config import DB_PATH, DATA_DIR, DB_VERSION, DEFAULT_SETTINGS, FAVICON_DIR


def get_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FAVICON_DIR, exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id INTEGER,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            favicon_path TEXT,
            default_browser TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            hour INTEGER NOT NULL,
            minute INTEGER NOT NULL,
            repeat_type TEXT NOT NULL DEFAULT 'once',
            repeat_days TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedule_bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            bookmark_id INTEGER NOT NULL,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
            FOREIGN KEY (bookmark_id) REFERENCES bookmarks(id) ON DELETE CASCADE,
            UNIQUE(schedule_id, bookmark_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS random_pools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            is_active INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pool_bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pool_id INTEGER NOT NULL,
            bookmark_id INTEGER NOT NULL,
            FOREIGN KEY (pool_id) REFERENCES random_pools(id) ON DELETE CASCADE,
            FOREIGN KEY (bookmark_id) REFERENCES bookmarks(id) ON DELETE CASCADE,
            UNIQUE(pool_id, bookmark_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS open_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bookmark_id INTEGER NOT NULL,
            opened_at TEXT DEFAULT (datetime('now', 'localtime')),
            opened_via TEXT DEFAULT 'manual',
            FOREIGN KEY (bookmark_id) REFERENCES bookmarks(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmark_tags (
            bookmark_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (bookmark_id, tag_id),
            FOREIGN KEY (bookmark_id) REFERENCES bookmarks(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookmarks_folder ON bookmarks(folder_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_bookmarks_url ON bookmarks(url)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_open_history_bookmark ON open_history(bookmark_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_open_history_time ON open_history(opened_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedules_active ON schedules(is_active)')

    for key, value in DEFAULT_SETTINGS.items():
        cursor.execute(
            'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
            (key, value)
        )

    _migrate_bookmarks_add_notes(cursor)
    _migrate_bookmarks_add_stats(cursor)
    _migrate_bookmarks_add_soft_delete(cursor)

    conn.commit()
    conn.close()


def _migrate_bookmarks_add_notes(cursor):
    cursor.execute("PRAGMA table_info(bookmarks)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'notes' not in columns:
        cursor.execute("ALTER TABLE bookmarks ADD COLUMN notes TEXT DEFAULT ''")


def _migrate_bookmarks_add_stats(cursor):
    cursor.execute("PRAGMA table_info(bookmarks)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'click_count' not in columns:
        cursor.execute("ALTER TABLE bookmarks ADD COLUMN click_count INTEGER DEFAULT 0")
    if 'last_opened_at' not in columns:
        cursor.execute("ALTER TABLE bookmarks ADD COLUMN last_opened_at TEXT")


def _migrate_bookmarks_add_soft_delete(cursor):
    cursor.execute("PRAGMA table_info(bookmarks)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'is_deleted' not in columns:
        cursor.execute("ALTER TABLE bookmarks ADD COLUMN is_deleted INTEGER DEFAULT 0")
    if 'deleted_at' not in columns:
        cursor.execute("ALTER TABLE bookmarks ADD COLUMN deleted_at TEXT")