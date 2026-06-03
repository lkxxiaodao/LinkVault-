import unittest
from unittest.mock import patch
from tests.data.base import BaseDataTest
from data.database import init_database


class TestDatabase(BaseDataTest):
    def test_init_database_creates_all_tables(self):
        conn = self._make_connection()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = {r['name'] for r in rows}
        expected = {
            'folders', 'bookmarks', 'schedules', 'schedule_bookmarks',
            'random_pools', 'pool_bookmarks', 'open_history', 'settings'
        }
        self.assertTrue(expected.issubset(table_names),
                        f'Missing tables: {expected - table_names}')
        conn.close()

    def test_init_database_creates_all_indices(self):
        conn = self._make_connection()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        index_names = {r['name'] for r in rows}
        expected = {
            'idx_bookmarks_folder', 'idx_bookmarks_url',
            'idx_open_history_bookmark', 'idx_open_history_time',
            'idx_schedules_active'
        }
        self.assertTrue(expected.issubset(index_names),
                        f'Missing indices: {expected - index_names}')
        conn.close()

    def test_init_database_inserts_default_settings(self):
        conn = self._make_connection()
        rows = conn.execute('SELECT key, value FROM settings').fetchall()
        settings = {r['key']: r['value'] for r in rows}
        self.assertIn('habit_analysis_enabled', settings)
        self.assertIn('first_run_completed', settings)
        self.assertIn('minimize_to_tray', settings)
        self.assertEqual(settings['habit_analysis_enabled'], '1')
        self.assertEqual(settings['first_run_completed'], '0')
        self.assertEqual(settings['minimize_to_tray'], '1')
        conn.close()

    def test_get_connection_returns_row_factory(self):
        conn = self._make_connection()
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('test_key', 'test_value')"
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM settings WHERE key = 'test_key'"
        ).fetchone()
        self.assertEqual(row['key'], 'test_key')
        self.assertEqual(row['value'], 'test_value')
        self.assertIsInstance(dict(row), dict)
        conn.close()

    def test_wal_mode_enabled(self):
        conn = self._make_connection()
        row = conn.execute('PRAGMA journal_mode').fetchone()
        self.assertEqual(row[0].upper(), 'WAL')
        conn.close()

    def test_foreign_keys_enabled(self):
        conn = self._make_connection()
        row = conn.execute('PRAGMA foreign_keys').fetchone()
        self.assertEqual(row[0], 1)
        conn.close()