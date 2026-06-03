import sys
import unittest
from unittest.mock import patch, MagicMock


class TestNotifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._mock_win11toast = MagicMock()
        cls._mock_toast = MagicMock()
        cls._mock_win11toast.toast = cls._mock_toast
        sys.modules['win11toast'] = cls._mock_win11toast

    @classmethod
    def tearDownClass(cls):
        if 'win11toast' in sys.modules:
            del sys.modules['win11toast']

    def setUp(self):
        self._mock_toast.reset_mock()

    def test_show_calls_toast(self):
        from infra.notifier import Notifier
        Notifier.show('Test Title', 'Test Message')
        self._mock_toast.assert_called_once_with('Test Title', 'Test Message', on_click=None)

    def test_show_with_callback(self):
        from infra.notifier import Notifier
        callback = lambda: None
        Notifier.show('Title', 'Message', on_click=callback)
        self._mock_toast.assert_called_once_with('Title', 'Message', on_click=callback)

    def test_show_graceful_degradation_no_win11toast(self):
        from infra.notifier import Notifier
        try:
            del sys.modules['win11toast']
            Notifier.show('Title', 'Message')
        except Exception as e:
            self.fail(f'Notifier.show() should not raise, got: {e}')
        finally:
            sys.modules['win11toast'] = self._mock_win11toast

    def test_schedule_notification_single_url(self):
        from infra.notifier import Notifier
        Notifier.show_schedule_notification(
            'Daily', ['https://example.com'], ['Example'], [1]
        )
        self._mock_toast.assert_called_once()
        call_args = self._mock_toast.call_args
        self.assertIn('Daily', call_args[0][0])
        self.assertIn('Example', call_args[0][1])

    def test_schedule_notification_multiple_urls(self):
        from infra.notifier import Notifier
        urls = ['https://a.com', 'https://b.com', 'https://c.com']
        titles = ['A', 'B', 'C']
        Notifier.show_schedule_notification('Multi', urls, titles, [1, 2, 3])
        self._mock_toast.assert_called_once()
        call_args = self._mock_toast.call_args
        self.assertIn('Multi', call_args[0][0])
        self.assertIn('3', call_args[0][1])

    def test_schedule_notification_truncates_long_titles(self):
        from infra.notifier import Notifier
        urls = ['https://a.com'] * 10
        titles = [f'Title {i}' for i in range(10)]
        Notifier.show_schedule_notification('Batch', urls, titles, list(range(10)))
        self._mock_toast.assert_called_once()
        call_args = self._mock_toast.call_args
        self.assertIn('10', call_args[0][1])

    def test_schedule_notification_on_click_opens_urls(self):
        from infra.notifier import Notifier
        Notifier.show_schedule_notification(
            'Test', ['https://example.com'], ['Example'], [1]
        )
        self._mock_toast.assert_called_once()
        self.assertIsNotNone(self._mock_toast.call_args[1].get('on_click'))