from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QCheckBox, QPushButton, QMessageBox, QFileDialog, QInputDialog, QLineEdit,
    QLabel, QListWidget, QListWidgetItem, QAbstractItemView, QGroupBox,
    QTreeWidget, QTreeWidgetItem, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
import os
from core.config_manager import ConfigManager
from core.folder_manager import FolderManager
from core.bookmark_manager import BookmarkManager
from infra.backup import BackupManager
from infra.auto_start import set_auto_start, is_auto_start_enabled
from infra.browser_launcher import BrowserLauncher, BROWSER_DEFINITIONS
from infra.global_hotkey import parse_hotkey_string, hotkey_to_display


class HotkeyCaptureLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._modifiers = 0
        self._vk = 0
        self.setReadOnly(True)
        self.setPlaceholderText('点击此处，然后按下组合键...')

    def keyPressEvent(self, event: QKeyEvent):
        modifiers = 0
        if event.modifiers() & Qt.ControlModifier:
            modifiers |= 0x0002
        if event.modifiers() & Qt.ShiftModifier:
            modifiers |= 0x0004
        if event.modifiers() & Qt.AltModifier:
            modifiers |= 0x0001
        if event.modifiers() & Qt.MetaModifier:
            modifiers |= 0x0008
        key = event.key()
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            self.setText(hotkey_to_display(modifiers, 0)[:-1])
            return
        if Qt.Key_A <= key <= Qt.Key_Z:
            vk = ord('A') + (key - Qt.Key_A)
            self._modifiers = modifiers
            self._vk = vk
            self.setText(hotkey_to_display(modifiers, vk))
            return
        if Qt.Key_0 <= key <= Qt.Key_9:
            vk = ord('0') + (key - Qt.Key_0)
            self._modifiers = modifiers
            self._vk = vk
            self.setText(hotkey_to_display(modifiers, vk))
            return
        if Qt.Key_F1 <= key <= Qt.Key_F12:
            vk = 0x70 + (key - Qt.Key_F1)
            self._modifiers = modifiers
            self._vk = vk
            self.setText(hotkey_to_display(modifiers, vk))
            return
        self.setText('')

    def get_modifiers_vk(self):
        return self._modifiers, self._vk

    def set_from_string(self, s):
        self._modifiers, self._vk = parse_hotkey_string(s)
        self.setText(hotkey_to_display(self._modifiers, self._vk))


class BackupFilterDialog(QDialog):
    """备份筛选对话框 - 允许用户选择要备份的文件夹和标签"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('选择备份内容')
        self.resize(450, 420)
        self.setModal(True)
        self._selected_folder_ids = []
        self._selected_tags = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(QLabel('选择要备份的书签范围（至少选一项）：'))

        folder_group = QGroupBox('按文件夹筛选')
        folder_layout = QVBoxLayout(folder_group)
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self._build_folder_tree()
        folder_layout.addWidget(self.folder_tree)
        layout.addWidget(folder_group)

        tag_group = QGroupBox('按标签筛选')
        tag_layout = QVBoxLayout(tag_group)
        self.tag_list = QListWidget()
        all_tags = BookmarkManager.get_all_tags()
        for t in all_tags:
            item = QListWidgetItem(f'{t["name"]} ({t["cnt"]})')
            item.setData(Qt.UserRole, t['name'])
            item.setCheckState(Qt.Unchecked)
            self.tag_list.addItem(item)
        tag_layout.addWidget(self.tag_list)
        layout.addWidget(tag_group)

        hint = QLabel('提示：文件夹和标签可同时选择，取并集。都不选则备份全部书签。')
        hint.setStyleSheet('color: #aaaaaa; font-size: 11px;')
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_select_all = QPushButton('全选')
        btn_select_all.clicked.connect(self._on_select_all)
        btn_clear = QPushButton('清除')
        btn_clear.clicked.connect(self._on_clear)
        btn_row.addWidget(btn_select_all)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        btn_ok = QPushButton('确认')
        btn_ok.clicked.connect(self._on_ok)
        btn_ok.setDefault(True)
        btn_cancel = QPushButton('取消')
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _build_folder_tree(self):
        self.folder_tree.clear()
        all_item = QTreeWidgetItem(self.folder_tree)
        all_item.setText(0, '全部书签')
        all_item.setData(0, Qt.UserRole, None)
        all_item.setCheckState(0, Qt.Unchecked)
        roots = FolderManager.get_roots()
        for folder in roots:
            self._insert_folder(self.folder_tree, folder)
        self.folder_tree.expandAll()

    def _insert_folder(self, parent, folder):
        item = QTreeWidgetItem(parent)
        item.setText(0, folder['name'])
        item.setData(0, Qt.UserRole, folder['id'])
        item.setCheckState(0, Qt.Unchecked)
        children = FolderManager.get_children(folder['id'])
        for child in children:
            self._insert_folder(item, child)
        return item

    def _collect_checked_folders(self, parent=None):
        if parent is None:
            parent = self.folder_tree.invisibleRootItem()
        ids = []
        for i in range(parent.childCount()):
            item = parent.child(i)
            if item.checkState(0) == Qt.Checked:
                fid = item.data(0, Qt.UserRole)
                if fid is not None:
                    ids.append(fid)
            ids.extend(self._collect_checked_folders(item))
        return ids

    def _on_ok(self):
        self._selected_folder_ids = self._collect_checked_folders()
        self._selected_tags = []
        for i in range(self.tag_list.count()):
            item = self.tag_list.item(i)
            if item.checkState() == Qt.Checked:
                self._selected_tags.append(item.data(Qt.UserRole))
        self.accept()

    def _on_select_all(self):
        self._set_all_check_state(Qt.Checked)

    def _on_clear(self):
        self._set_all_check_state(Qt.Unchecked)

    def _set_all_check_state(self, state):
        def set_recursive(parent):
            for i in range(parent.childCount()):
                item = parent.child(i)
                item.setCheckState(0, state)
                set_recursive(item)
        set_recursive(self.folder_tree.invisibleRootItem())
        for i in range(self.tag_list.count()):
            self.tag_list.item(i).setCheckState(state)

    def get_selection(self):
        return self._selected_folder_ids, self._selected_tags


class SettingsDialog(QDialog):
    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle('设置')
        self.resize(500, 440)
        self.setModal(True)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        notebook = QTabWidget()
        layout.addWidget(notebook)

        general_tab = QWidget()
        gen_layout = QVBoxLayout(general_tab)
        gen_layout.setContentsMargins(12, 12, 12, 12)
        gen_layout.setSpacing(12)

        self.habit_check = QCheckBox('启用智能习惯感知（完全离线分析）')
        gen_layout.addWidget(self.habit_check)

        self.tray_check = QCheckBox('关闭窗口时最小化到系统托盘')
        gen_layout.addWidget(self.tray_check)

        self.auto_start_check = QCheckBox('开机时自动启动 LinkVault')
        gen_layout.addWidget(self.auto_start_check)

        self._auto_start_hint = QLabel('将注册为 Windows 开机自启项，可在任务管理器中管理')
        self._auto_start_hint.setStyleSheet('color: #aaaaaa; font-size: 11px;')
        self._auto_start_hint.setWordWrap(True)
        gen_layout.addWidget(self._auto_start_hint)

        theme_row = QHBoxLayout()
        theme_row.addWidget(QLabel('界面主题：'))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            '浅色蓝 (light_blue.xml)',
            '浅色青 (light_cyan.xml)',
            '浅色绿 (light_teal.xml)',
            '浅色粉 (light_pink.xml)',
            '深色蓝 (dark_blue.xml)',
            '深色青 (dark_cyan.xml)',
            '深色绿 (dark_teal.xml)',
            '深色粉 (dark_pink.xml)',
            '深色琥珀 (dark_amber.xml)',
        ])
        self.theme_combo.setMinimumWidth(200)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        gen_layout.addLayout(theme_row)

        theme_hint = QLabel('切换主题将立即生效')
        theme_hint.setStyleSheet('color: #888888; font-size: 11px;')
        gen_layout.addWidget(theme_hint)

        gen_layout.addStretch()

        btn_save = QPushButton('保存设置')
        btn_save.clicked.connect(self._on_save_settings)
        gen_layout.addWidget(btn_save)

        notebook.addTab(general_tab, '常规')

        backup_tab = QWidget()
        bk_layout = QVBoxLayout(backup_tab)
        bk_layout.setContentsMargins(12, 12, 12, 12)
        bk_layout.setSpacing(8)

        btn_export = QPushButton('导出 .linkvault 加密备份...')
        btn_export.clicked.connect(self._on_export_backup)
        bk_layout.addWidget(btn_export)

        btn_import = QPushButton('导入 .linkvault 备份...')
        btn_import.clicked.connect(self._on_import_backup)
        bk_layout.addWidget(btn_import)

        btn_html = QPushButton('导出 HTML 书签文件...')
        btn_html.clicked.connect(self._on_export_html)
        bk_layout.addWidget(btn_html)

        bk_layout.addStretch()

        notebook.addTab(backup_tab, '备份')

        browser_tab = QWidget()
        br_layout = QVBoxLayout(browser_tab)
        br_layout.setContentsMargins(12, 12, 12, 12)
        br_layout.setSpacing(8)

        br_layout.addWidget(QLabel('已检测到的浏览器：'))

        self.browser_list = QListWidget()
        self.browser_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.browser_list.setAlternatingRowColors(True)
        br_layout.addWidget(self.browser_list, 1)

        btn_row = QHBoxLayout()

        self.btn_add_browser = QPushButton('手动添加浏览器...')
        self.btn_add_browser.clicked.connect(self._on_add_browser)
        btn_row.addWidget(self.btn_add_browser)

        self.btn_remove_browser = QPushButton('移除选中浏览器')
        self.btn_remove_browser.clicked.connect(self._on_remove_browser)
        self.btn_remove_browser.setEnabled(False)
        btn_row.addWidget(self.btn_remove_browser)

        btn_row.addStretch()
        br_layout.addLayout(btn_row)

        note = QLabel('提示：手动添加的浏览器可以移除；\n自动检测到的浏览器无法移除，卸载后自动消失。')
        note.setStyleSheet('color: #888; font-size: 11px;')
        note.setWordWrap(True)
        br_layout.addWidget(note)

        notebook.addTab(browser_tab, '浏览器')

        hotkey_tab = QWidget()
        hk_layout = QVBoxLayout(hotkey_tab)
        hk_layout.setContentsMargins(12, 12, 12, 12)
        hk_layout.setSpacing(12)

        hk_layout.addWidget(QLabel('<b>搜索快捷键</b>'))
        hk_layout.addWidget(QLabel('按下此快捷键可在任意界面呼出快速搜索弹窗'))

        self.hotkey_edit = HotkeyCaptureLineEdit()
        self.hotkey_edit.setMinimumHeight(36)
        hk_layout.addWidget(self.hotkey_edit)

        self.hotkey_status = QLabel('')
        self.hotkey_status.setStyleSheet('color: #888; font-size: 11px;')
        hk_layout.addWidget(self.hotkey_status)

        btn_apply_hotkey = QPushButton('应用搜索快捷键')
        btn_apply_hotkey.clicked.connect(self._on_apply_hotkey)
        hk_layout.addWidget(btn_apply_hotkey)

        hk_layout.addSpacing(8)

        hk_layout.addWidget(QLabel('<b>快速捕获快捷键</b>'))
        hk_layout.addWidget(QLabel('按下此快捷键可在任意界面快速添加书签（自动填入剪贴板网址）'))

        self.capture_hotkey_edit = HotkeyCaptureLineEdit()
        self.capture_hotkey_edit.setMinimumHeight(36)
        hk_layout.addWidget(self.capture_hotkey_edit)

        self.capture_hotkey_status = QLabel('')
        self.capture_hotkey_status.setStyleSheet('color: #888; font-size: 11px;')
        hk_layout.addWidget(self.capture_hotkey_status)

        btn_apply_capture = QPushButton('应用捕获快捷键')
        btn_apply_capture.clicked.connect(self._on_apply_capture_hotkey)
        hk_layout.addWidget(btn_apply_capture)

        hk_layout.addStretch()

        notebook.addTab(hotkey_tab, '快捷键')

    def _load_settings(self):
        self.habit_check.setChecked(ConfigManager.get_bool('habit_analysis_enabled', True))
        self.tray_check.setChecked(ConfigManager.get_bool('minimize_to_tray', True))
        self.auto_start_check.setChecked(is_auto_start_enabled())
        self._refresh_browser_list()
        hotkey_str = ConfigManager.get('global_hotkey', 'Ctrl+Shift+L')
        self.hotkey_edit.set_from_string(hotkey_str)
        capture_str = ConfigManager.get('capture_hotkey', 'Ctrl+Shift+N')
        self.capture_hotkey_edit.set_from_string(capture_str)
        theme = ConfigManager.get('theme', 'dark_blue.xml')
        theme_index = 0
        for i in range(self.theme_combo.count()):
            if theme in self.theme_combo.itemText(i):
                theme_index = i
                break
        self.theme_combo.setCurrentIndex(theme_index)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)

    def _on_save_settings(self):
        ConfigManager.set_bool('habit_analysis_enabled', self.habit_check.isChecked())
        ConfigManager.set_bool('minimize_to_tray', self.tray_check.isChecked())
        auto_start = self.auto_start_check.isChecked()
        ConfigManager.set_bool('auto_start', auto_start)
        set_auto_start(auto_start)
        QMessageBox.information(self, '设置已保存', '设置已保存成功')

    def _on_theme_changed(self, index):
        if not hasattr(self, 'theme_combo') or self._app is None:
            return
        text = self.theme_combo.itemText(index)
        theme_name = text.split('(')[-1].rstrip(')')
        self._app.set_theme(theme_name)

    def _on_export_backup(self):
        dlg = BackupFilterDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        folder_ids, tag_names = dlg.get_selection()

        filepath, _ = QFileDialog.getSaveFileName(
            self, '导出加密备份', '', 'LinkVault 备份 (*.linkvault)')
        if not filepath:
            return
        password, ok = QInputDialog.getText(self, '设置密码', '请设置备份密码：', echo=QLineEdit.Password)
        if not ok or not password:
            return
        try:
            BackupManager.export_linkvault(filepath, password, folder_ids or None, tag_names or None)
            QMessageBox.information(self, '导出成功', f'备份已成功导出到：{filepath}')
        except Exception as e:
            QMessageBox.critical(self, '导出失败', f'导出过程中发生错误：{e}')

    def _on_import_backup(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, '导入加密备份', '', 'LinkVault 备份 (*.linkvault)')
        if not filepath:
            return
        password, ok = QInputDialog.getText(self, '输入密码', '请输入备份密码：', echo=QLineEdit.Password)
        if not ok or not password:
            return
        if QMessageBox.question(self, '确认导入', '导入将合并备份中的数据，确定继续吗？') == QMessageBox.Yes:
            try:
                BackupManager.import_linkvault(filepath, password)
                QMessageBox.information(self, '导入成功', '备份已成功导入')
            except Exception as e:
                QMessageBox.critical(self, '导入失败', f'导入过程中发生错误：{e}')

    def _on_export_html(self):
        dlg = BackupFilterDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        folder_ids, tag_names = dlg.get_selection()

        filepath, _ = QFileDialog.getSaveFileName(
            self, '导出 HTML 书签', '', 'HTML 书签文件 (*.html)')
        if not filepath:
            return
        try:
            BackupManager.export_html(filepath, folder_ids or None, tag_names or None)
            QMessageBox.information(self, '导出成功', f'书签已成功导出为 HTML：{filepath}')
        except Exception as e:
            QMessageBox.critical(self, '导出失败', f'导出过程中发生错误：{e}')

    def _refresh_browser_list(self):
        self.browser_list.clear()
        installed = BrowserLauncher.get_installed_browsers()
        for name, path in installed.items():
            if name.startswith('__custom__'):
                display_name = name[len('__custom__'):] + ' (手动添加)'
            else:
                info = BROWSER_DEFINITIONS.get(name, {})
                display_name = info.get('name', name)
            item = QListWidgetItem(f'{display_name}\n    {path}')
            item.setData(Qt.UserRole, {'name': name, 'path': path, 'is_custom': name.startswith('__custom__')})
            self.browser_list.addItem(item)
        self.browser_list.itemSelectionChanged.connect(self._on_browser_selection_changed)
        self._on_browser_selection_changed()

    def _on_browser_selection_changed(self):
        item = self.browser_list.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            self.btn_remove_browser.setEnabled(data.get('is_custom', False))
        else:
            self.btn_remove_browser.setEnabled(False)

    def _on_add_browser(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, '选择浏览器程序', '',
            '可执行文件 (*.exe);;所有文件 (*.*)')
        if not filepath:
            return
        if not os.path.isfile(filepath):
            return
        basename = os.path.splitext(os.path.basename(filepath))[0]
        name, ok = QInputDialog.getText(
            self, '浏览器名称', '请输入浏览器显示名称：', text=basename)
        if not ok or not name.strip():
            return
        BrowserLauncher.add_custom_browser(name.strip(), filepath)
        self._refresh_browser_list()

    def _on_remove_browser(self):
        item = self.browser_list.currentItem()
        if not item:
            return
        data = item.data(Qt.UserRole)
        if not data.get('is_custom', False):
            return
        BrowserLauncher.remove_custom_browser(data['path'])
        self._refresh_browser_list()

    def _on_apply_hotkey(self):
        modifiers, vk = self.hotkey_edit.get_modifiers_vk()
        if vk == 0:
            self.hotkey_status.setText('请先设置有效的快捷键组合')
            self.hotkey_status.setStyleSheet('color: #e57373; font-size: 11px;')
            return
        display = hotkey_to_display(modifiers, vk)
        if self._app:
            ok, result = self._app.update_hotkey(display)
            if ok:
                self.hotkey_status.setText(f'快捷键已设置为 {result}（即时生效）')
                self.hotkey_status.setStyleSheet('color: #81c784; font-size: 11px;')
            else:
                self.hotkey_status.setText(f'{display} 注册失败，可能与其他软件冲突')
                self.hotkey_status.setStyleSheet('color: #e57373; font-size: 11px;')
        else:
            ConfigManager.set('global_hotkey', display)
            self.hotkey_status.setText(f'快捷键已保存为 {display}（重启后生效）')
            self.hotkey_status.setStyleSheet('color: #81c784; font-size: 11px;')

    def _on_apply_capture_hotkey(self):
        modifiers, vk = self.capture_hotkey_edit.get_modifiers_vk()
        if vk == 0:
            self.capture_hotkey_status.setText('请先设置有效的快捷键组合')
            self.capture_hotkey_status.setStyleSheet('color: #e57373; font-size: 11px;')
            return
        display = hotkey_to_display(modifiers, vk)
        if self._app:
            ok, result = self._app.update_capture_hotkey(display)
            if ok:
                self.capture_hotkey_status.setText(f'捕获快捷键已设置为 {result}（即时生效）')
                self.capture_hotkey_status.setStyleSheet('color: #81c784; font-size: 11px;')
            else:
                self.capture_hotkey_status.setText(f'{display} 注册失败，可能与其他软件冲突')
                self.capture_hotkey_status.setStyleSheet('color: #e57373; font-size: 11px;')
        else:
            ConfigManager.set('capture_hotkey', display)
            self.capture_hotkey_status.setText(f'捕获快捷键已保存为 {display}（重启后生效）')
            self.capture_hotkey_status.setStyleSheet('color: #81c784; font-size: 11px;')