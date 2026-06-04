import sys
import os
import tempfile
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QLockFile
from qt_material import apply_stylesheet

from data.database import init_database
from ui_qt.main_window import MainWindow
from ui_qt.dialogs.quick_search_dialog import QuickSearchDialog
from ui_qt.dialogs.quick_capture_dialog import QuickCaptureDialog
from core.schedule_engine import ScheduleEngine
from core.habit_analyzer import HabitAnalyzer
from core.config_manager import ConfigManager
from infra.auto_start import is_auto_start_enabled, set_auto_start
from infra.global_hotkey import GlobalHotkey, parse_hotkey_string, hotkey_to_display


class LinkVaultApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName('LinkVault')
        self.app.setOrganizationName('LinkVault')

        self._current_theme = ConfigManager.get('theme', 'dark_blue.xml')
        apply_stylesheet(self.app, theme=self._current_theme, invert_secondary=True)

        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            self.app.setWindowIcon(QIcon(icon_path))

        self.tray_icon = None
        self._setup_tray()

        self.main_window = MainWindow(self)
        self._quick_search = QuickSearchDialog()
        self._quick_capture = QuickCaptureDialog()
        self._quick_capture.bookmark_saved.connect(self._on_bookmark_saved)
        self._setup_global_hotkey()
        self._setup_capture_hotkey()

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon()
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.app.style().standardIcon(
                self.app.style().StandardPixmap.SP_ComputerIcon))

        self._tray_menu = QMenu()
        self._tray_show_action = QAction('显示主窗口')
        self._tray_show_action.triggered.connect(self.show_window)
        self._tray_menu.addAction(self._tray_show_action)

        self._tray_menu.addSeparator()

        self._tray_quit_action = QAction('退出 LinkVault')
        self._tray_quit_action.triggered.connect(self.quit_app)
        self._tray_menu.addAction(self._tray_quit_action)

        self.tray_icon.setContextMenu(self._tray_menu)
        self.tray_icon.setToolTip('LinkVault')
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()

    def show_window(self):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _setup_global_hotkey(self):
        hotkey_str = ConfigManager.get('global_hotkey', 'Ctrl+Shift+L')
        modifiers, vk = parse_hotkey_string(hotkey_str)
        self._hotkey = GlobalHotkey(self._show_quick_search, modifiers, vk)
        ok = self._hotkey.register()
        if ok:
            self.app.installNativeEventFilter(self._hotkey)
        else:
            print('全局热键注册失败，可能是与其他软件冲突')

    def _show_quick_search(self):
        self._quick_search.show_and_focus()

    def _setup_capture_hotkey(self):
        hotkey_str = ConfigManager.get('capture_hotkey', 'Ctrl+Shift+N')
        modifiers, vk = parse_hotkey_string(hotkey_str)
        self._capture_hotkey = GlobalHotkey(self._show_quick_capture, modifiers, vk, hotkey_id=2)
        ok = self._capture_hotkey.register()
        if ok:
            self.app.installNativeEventFilter(self._capture_hotkey)
        else:
            print('快速捕获热键注册失败')

    def _show_quick_capture(self):
        self._quick_capture.show_and_focus()

    def _on_bookmark_saved(self):
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'bookmark_list'):
            self.main_window.bookmark_list._refresh()

    def update_hotkey(self, hotkey_str):
        modifiers, vk = parse_hotkey_string(hotkey_str)
        ok = self._hotkey.reregister(modifiers, vk)
        if ok:
            ConfigManager.set('global_hotkey', hotkey_str)
            display = hotkey_to_display(modifiers, vk)
            return True, display
        return False, ''

    def update_capture_hotkey(self, hotkey_str):
        modifiers, vk = parse_hotkey_string(hotkey_str)
        ok = self._capture_hotkey.reregister(modifiers, vk)
        if ok:
            ConfigManager.set('capture_hotkey', hotkey_str)
            display = hotkey_to_display(modifiers, vk)
            return True, display
        return False, ''

    def set_theme(self, theme_name):
        self._current_theme = theme_name
        ConfigManager.set('theme', theme_name)
        apply_stylesheet(self.app, theme=theme_name, invert_secondary=True)

    def get_theme(self):
        return self._current_theme

    def quit_app(self):
        if hasattr(self, '_hotkey'):
            self._hotkey.unregister()
        if hasattr(self, '_capture_hotkey'):
            self._capture_hotkey.unregister()
        if self.tray_icon:
            self.tray_icon.hide()
        ScheduleEngine().stop()
        self.app.quit()

    def run(self):
        self._sync_auto_start()
        ScheduleEngine().start()
        self._check_habits()
        self.main_window.show()
        sys.exit(self.app.exec())

    def _sync_auto_start(self):
        config_enabled = ConfigManager.get_bool('auto_start', False)
        if config_enabled:
            set_auto_start(True)
        else:
            actual_enabled = is_auto_start_enabled()
            if actual_enabled:
                set_auto_start(False)

    def _check_habits(self):
        if HabitAnalyzer.is_enabled():
            suggestions = HabitAnalyzer.analyze()
            if suggestions:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(2000, lambda: self._show_habit_card(suggestions))

    def _show_habit_card(self, suggestions):
        from ui_qt.habit_card import HabitCard
        card = HabitCard(self.main_window)
        card.show_suggestions(suggestions)


def run_app():
    lock_file = QLockFile(os.path.join(tempfile.gettempdir(), 'linkvault.lock'))
    if not lock_file.tryLock(100):
        print('LinkVault 已在运行中，不能重复打开')
        sys.exit(0)

    init_database()
    app = LinkVaultApp()
    app._lock_file = lock_file
    app.run()


if __name__ == '__main__':
    run_app()