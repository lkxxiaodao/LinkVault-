import unittest
from unittest.mock import patch, MagicMock


class TestBrowserLauncher(unittest.TestCase):
    def test_get_installed_browsers_returns_dict(self):
        from infra.browser_launcher import BrowserLauncher
        browsers = BrowserLauncher.get_installed_browsers()
        self.assertIsInstance(browsers, dict)

    @patch('infra.browser_launcher.os.path.exists')
    def test_get_installed_browsers_with_existing_paths(self, mock_exists):
        from infra.browser_launcher import BrowserLauncher
        mock_exists.return_value = True
        browsers = BrowserLauncher.get_installed_browsers()
        self.assertIn('chrome', browsers)
        self.assertIn('edge', browsers)
        self.assertIn('firefox', browsers)
        self.assertEqual(browsers['chrome'], r'C:\Program Files\Google\Chrome\Application\chrome.exe')

    @patch('infra.browser_launcher.os.path.exists')
    def test_get_installed_browsers_none_found(self, mock_exists):
        from infra.browser_launcher import BrowserLauncher
        mock_exists.return_value = False
        browsers = BrowserLauncher.get_installed_browsers()
        self.assertEqual(browsers, {})

    @patch('infra.browser_launcher.webbrowser.open')
    def test_open_url_with_default_browser(self, mock_web_open):
        from infra.browser_launcher import BrowserLauncher
        BrowserLauncher.open_url('https://example.com')
        mock_web_open.assert_called_once_with('https://example.com')

    @patch('infra.browser_launcher.subprocess.Popen')
    @patch('infra.browser_launcher.os.path.exists')
    def test_open_url_with_specific_browser(self, mock_exists, mock_popen):
        from infra.browser_launcher import BrowserLauncher
        mock_exists.return_value = True
        BrowserLauncher.open_url('https://example.com', browser_path=r'C:\browser.exe')
        mock_popen.assert_called_once_with([r'C:\browser.exe', 'https://example.com'])

    @patch('infra.browser_launcher.webbrowser.open')
    @patch('infra.browser_launcher.os.path.exists')
    def test_open_url_falls_back_when_browser_not_found(self, mock_exists, mock_web_open):
        from infra.browser_launcher import BrowserLauncher
        mock_exists.return_value = False
        BrowserLauncher.open_url('https://example.com', browser_path=r'C:\nonexistent.exe')
        mock_web_open.assert_called_once_with('https://example.com')

    @patch('infra.browser_launcher.winreg.QueryValue')
    @patch('infra.browser_launcher.winreg.OpenKey')
    @patch('infra.browser_launcher.os.path.exists')
    def test_get_installed_browsers_from_registry(self, mock_exists, mock_openkey, mock_query):
        def exists_side_effect(path):
            hardcoded_paths = [
                r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
                r'C:\Program Files\Mozilla Firefox\firefox.exe',
                r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe',
            ]
            return path not in hardcoded_paths

        mock_exists.side_effect = exists_side_effect
        mock_query.return_value = r'C:\Registry\Chrome\chrome.exe'

        from infra.browser_launcher import BrowserLauncher
        browsers = BrowserLauncher.get_installed_browsers()
        self.assertIn('chrome', browsers)