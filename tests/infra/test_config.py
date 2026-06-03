import os
import sys
import unittest
from unittest.mock import patch


class TestConfig(unittest.TestCase):
    def test_app_name(self):
        from infra.config import APP_NAME
        self.assertEqual(APP_NAME, 'LinkVault')

    def test_app_version(self):
        from infra.config import APP_VERSION
        self.assertEqual(APP_VERSION, '1.0.0')

    def test_db_version(self):
        from infra.config import DB_VERSION
        self.assertEqual(DB_VERSION, 1)

    def test_data_dir_in_appdata(self):
        from infra.config import DATA_DIR
        self.assertIn('LinkVault', DATA_DIR)

    def test_db_path_inside_data_dir(self):
        from infra.config import DATA_DIR, DB_PATH
        self.assertTrue(DB_PATH.startswith(DATA_DIR))
        self.assertTrue(DB_PATH.endswith('linkvault.db'))

    def test_log_path_inside_data_dir(self):
        from infra.config import DATA_DIR, LOG_PATH
        self.assertTrue(LOG_PATH.startswith(DATA_DIR))
        self.assertTrue(LOG_PATH.endswith('linkvault.log'))

    def test_favicon_dir_inside_data_dir(self):
        from infra.config import DATA_DIR, FAVICON_DIR
        self.assertTrue(FAVICON_DIR.startswith(DATA_DIR))
        self.assertTrue(FAVICON_DIR.endswith('favicons'))

    def test_assets_dir_exists(self):
        from infra.config import ASSETS_DIR
        self.assertTrue(os.path.isdir(ASSETS_DIR))

    def test_default_settings_keys(self):
        from infra.config import DEFAULT_SETTINGS
        self.assertIn('habit_analysis_enabled', DEFAULT_SETTINGS)
        self.assertIn('first_run_completed', DEFAULT_SETTINGS)
        self.assertIn('minimize_to_tray', DEFAULT_SETTINGS)
        self.assertEqual(DEFAULT_SETTINGS['habit_analysis_enabled'], '1')
        self.assertEqual(DEFAULT_SETTINGS['first_run_completed'], '0')
        self.assertEqual(DEFAULT_SETTINGS['minimize_to_tray'], '1')

    def test_habit_analysis_constants(self):
        from infra.config import HABIT_ANALYSIS_DAYS, HABIT_CONSECUTIVE_DAYS, HABIT_TIME_SLOT_HOURS
        self.assertEqual(HABIT_ANALYSIS_DAYS, 30)
        self.assertEqual(HABIT_CONSECUTIVE_DAYS, 3)
        self.assertEqual(HABIT_TIME_SLOT_HOURS, 2)

    def test_frozen_vs_dev_base_dir(self):
        with patch.object(sys, 'frozen', True, create=True):
            with patch.object(sys, 'executable', '/fake/path/linkvault.exe', create=True):
                import importlib
                import infra.config
                importlib.reload(infra.config)
                self.assertEqual(infra.config.BASE_DIR, '/fake/path')

        importlib.reload(infra.config)