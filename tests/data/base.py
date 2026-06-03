import os
import tempfile
import sqlite3
import unittest
from unittest.mock import patch

_REPO_MODULES = [
    'data.bookmark_repo',
    'data.folder_repo',
    'data.schedule_repo',
    'data.pool_repo',
    'data.history_repo',
]


class BaseDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp_dir = tempfile.TemporaryDirectory()
        cls._db_path = os.path.join(cls._temp_dir.name, 'test.db')
        conn = sqlite3.connect(cls._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        cls._create_tables(conn)
        cls._create_indices(conn)
        cls._insert_default_settings(conn)
        conn.commit()
        conn.close()

    @classmethod
    def _create_tables(cls, conn):
        conn.executescript('''
            CREATE TABLE folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE CASCADE
            );

            CREATE TABLE bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id INTEGER,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                favicon_path TEXT,
                default_browser TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
            );

            CREATE TABLE schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                hour INTEGER NOT NULL,
                minute INTEGER NOT NULL,
                repeat_type TEXT NOT NULL DEFAULT 'once',
                repeat_days TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE schedule_bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER NOT NULL,
                bookmark_id INTEGER NOT NULL,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE,
                FOREIGN KEY (bookmark_id) REFERENCES bookmarks(id) ON DELETE CASCADE,
                UNIQUE(schedule_id, bookmark_id)
            );

            CREATE TABLE random_pools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE pool_bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pool_id INTEGER NOT NULL,
                bookmark_id INTEGER NOT NULL,
                FOREIGN KEY (pool_id) REFERENCES random_pools(id) ON DELETE CASCADE,
                FOREIGN KEY (bookmark_id) REFERENCES bookmarks(id) ON DELETE CASCADE,
                UNIQUE(pool_id, bookmark_id)
            );

            CREATE TABLE open_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bookmark_id INTEGER NOT NULL,
                opened_at TEXT DEFAULT (datetime('now', 'localtime')),
                opened_via TEXT DEFAULT 'manual',
                FOREIGN KEY (bookmark_id) REFERENCES bookmarks(id) ON DELETE CASCADE
            );

            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        ''')

    @classmethod
    def _create_indices(cls, conn):
        conn.executescript('''
            CREATE INDEX idx_bookmarks_folder ON bookmarks(folder_id);
            CREATE INDEX idx_bookmarks_url ON bookmarks(url);
            CREATE INDEX idx_open_history_bookmark ON open_history(bookmark_id);
            CREATE INDEX idx_open_history_time ON open_history(opened_at);
            CREATE INDEX idx_schedules_active ON schedules(is_active);
        ''')

    @classmethod
    def _insert_default_settings(cls, conn):
        conn.executescript('''
            INSERT OR IGNORE INTO settings (key, value) VALUES ('habit_analysis_enabled', '1');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('first_run_completed', '0');
            INSERT OR IGNORE INTO settings (key, value) VALUES ('minimize_to_tray', '1');
        ''')

    def _make_connection(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def setUp(self):
        self._patchers = [
            patch(f'{mod}.get_connection', side_effect=self._make_connection)
            for mod in _REPO_MODULES
        ]
        self._patchers.append(
            patch('data.database.get_connection', side_effect=self._make_connection)
        )
        for p in self._patchers:
            p.start()
        self._clean_all_tables()

    def tearDown(self):
        for p in self._patchers:
            p.stop()

    def _clean_all_tables(self):
        conn = self._make_connection()
        try:
            tables = [
                'open_history', 'pool_bookmarks', 'schedule_bookmarks',
                'bookmarks', 'folders', 'schedules', 'random_pools'
            ]
            for t in tables:
                conn.execute(f'DELETE FROM {t}')
            conn.execute("DELETE FROM sqlite_sequence")
            conn.commit()
        finally:
            conn.close()