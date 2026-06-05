from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QTabWidget, QWidget, QVBoxLayout,
    QHBoxLayout, QMenuBar, QMenu, QMessageBox, QFileDialog, QInputDialog, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QFrame, QDialog,
    QLineEdit, QComboBox, QSpinBox, QCheckBox, QRadioButton, QButtonGroup,
    QSizePolicy, QAbstractItemView, QApplication
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QAction

from infra.backup import BackupManager
from infra.bookmark_importer import import_bookmarks_from_html
from core.schedule_engine import ScheduleEngine
from core.random_walker import RandomWalker
from data.schedule_repo import ScheduleRepo
from data.bookmark_repo import BookmarkRepo
from ui_qt.folder_tree import FolderTree
from ui_qt.bookmark_list import BookmarkList
from ui_qt.search_bar import SearchBar
from ui_qt.random_walk_bar import RandomWalkBar


class _BackupWorker(QThread):
    """后台线程执行导入导出操作"""
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._action = None
        self._args = ()
        self._kwargs = {}

    def run_import(self, filepath, password):
        self._action = 'import'
        self._args = (filepath, password)
        self.start()

    def run_export_linkvault(self, filepath, password, folder_ids, tag_names):
        self._action = 'export'
        self._args = (filepath, password, folder_ids, tag_names)
        self.start()

    def run_export_html(self, filepath, folder_ids, tag_names):
        self._action = 'export_html'
        self._args = (filepath, folder_ids, tag_names)
        self.start()

    def run_import_browser_bookmarks(self, filepath):
        self._action = 'import_browser_bookmarks'
        self._args = (filepath,)
        self.start()

    def run(self):
        try:
            if self._action == 'import':
                BackupManager.import_linkvault(*self._args)
                self.finished.emit('import')
            elif self._action == 'export':
                BackupManager.export_linkvault(*self._args)
                self.finished.emit('export')
            elif self._action == 'export_html':
                BackupManager.export_html(*self._args)
                self.finished.emit('export_html')
            elif self._action == 'import_browser_bookmarks':
                imported, skipped = import_bookmarks_from_html(*self._args)
                self.finished.emit(('import_browser_bookmarks', imported, skipped))
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self.setWindowTitle('LinkVault')
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

        self._setup_menu()
        self._setup_central()
        self._setup_random_walk_bar()
        self._load_schedule_list()
        self._load_pool_list()

    def _on_tab_changed(self, index):
        if self.notebook.tabText(index) == '回收站':
            self._load_trash_list()
        elif self.notebook.tabText(index) == '定时任务':
            self._load_schedule_list()
        elif self.notebook.tabText(index) == '随机池':
            self._load_pool_list()

    def _setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu('文件')
        file_menu.addAction('导入备份...', self._on_import)
        file_menu.addAction('导入浏览器收藏夹...', self._on_import_browser_bookmarks)
        file_menu.addAction('导出备份...', self._on_export)
        file_menu.addAction('导出 HTML...', self._on_export_html)
        file_menu.addSeparator()
        file_menu.addAction('设置...', self._on_settings)
        file_menu.addSeparator()
        file_menu.addAction('退出', self._app.quit_app)

    def _setup_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 0)
        layout.setSpacing(4)

        self.search_bar = SearchBar(on_results=self._on_search_results)
        layout.addWidget(self.search_bar)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)
        self.folder_tree = FolderTree()
        self.folder_tree.folder_selected.connect(self._on_folder_selected)
        self.folder_tree.pool_changed.connect(self._on_pool_changed)
        left_layout.addWidget(self.folder_tree)
        splitter.addWidget(left)
        splitter.setStretchFactor(0, 0)
        left.setMaximumWidth(310)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.notebook = QTabWidget()
        right_layout.addWidget(self.notebook)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)

        self._setup_bookmark_tab()
        self._setup_schedule_tab()
        self._setup_pool_tab()
        self._setup_trash_tab()

        self.notebook.currentChanged.connect(self._on_tab_changed)

    def _setup_bookmark_tab(self):
        self.bookmark_list = BookmarkList(on_refresh_pools=self._on_pool_changed)
        self.notebook.addTab(self.bookmark_list, '书签')

    def _setup_schedule_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        toolbar = QWidget()
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(4)
        btn_add = QPushButton('+ 新建任务')
        btn_add.clicked.connect(self._on_schedule_add)
        btn_edit = QPushButton('编辑')
        btn_edit.clicked.connect(self._on_schedule_edit)
        btn_del = QPushButton('删除')
        btn_del.clicked.connect(self._on_schedule_delete)
        btn_toggle = QPushButton('启用/禁用')
        btn_toggle.clicked.connect(self._on_schedule_toggle)
        tb_layout.addWidget(btn_add)
        tb_layout.addWidget(btn_edit)
        tb_layout.addWidget(btn_del)
        tb_layout.addWidget(btn_toggle)
        tb_layout.addStretch()
        layout.addWidget(toolbar)

        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(4)
        self.schedule_table.setHorizontalHeaderLabels(['任务名称', '时间', '重复规则', '状态'])
        self.schedule_table.horizontalHeader().setStretchLastSection(True)
        self.schedule_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.schedule_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.schedule_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.schedule_table.verticalHeader().setVisible(False)
        layout.addWidget(self.schedule_table)

        self._setup_schedule_form(layout)

        self.notebook.addTab(tab, '定时任务')

    def _setup_schedule_form(self, parent_layout):
        self.sched_form = QFrame()
        self.sched_form.setFrameStyle(QFrame.StyledPanel)
        self.sched_form.hide()
        form_layout = QVBoxLayout(self.sched_form)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(8)

        title_label = QLabel('编辑定时任务')
        title_label.setProperty('class', 'h2')
        form_layout.addWidget(title_label)
        self._sched_form_title = title_label

        row1 = QHBoxLayout()
        row1.addWidget(QLabel('任务名称：'))
        self.sched_name_edit = QLineEdit()
        self.sched_name_edit.setPlaceholderText('输入任务名称')
        row1.addWidget(self.sched_name_edit)
        form_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel('时间：'))
        self.sched_hour_spin = QSpinBox()
        self.sched_hour_spin.setRange(0, 23)
        self.sched_hour_spin.setValue(9)
        self.sched_hour_spin.setPrefix('')
        row2.addWidget(self.sched_hour_spin)
        row2.addWidget(QLabel(':'))
        self.sched_minute_spin = QSpinBox()
        self.sched_minute_spin.setRange(0, 59)
        self.sched_minute_spin.setValue(0)
        row2.addWidget(self.sched_minute_spin)
        row2.addStretch()
        form_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel('重复规则：'))
        self.sched_repeat_group = QButtonGroup()
        repeat_options = [
            ('仅一次', 'once'), ('每天', 'daily'), ('工作日', 'weekdays'),
            ('每周', 'weekly'), ('每月', 'monthly'),
        ]
        self.sched_repeat_radios = {}
        for i, (label, value) in enumerate(repeat_options):
            rb = QRadioButton(label)
            self.sched_repeat_group.addButton(rb, i)
            self.sched_repeat_radios[value] = rb
            row3.addWidget(rb)
            if value == 'daily':
                rb.setChecked(True)
        row3.addStretch()
        form_layout.addLayout(row3)

        self.sched_repeat_group.buttonClicked.connect(self._on_sched_repeat_changed)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel('重复日：'))
        self._sched_repeat_day_label = row4.itemAt(row4.count() - 1).widget()

        # 每周的星期选择
        self.sched_day_checks = {}
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        for i, name in enumerate(weekdays):
            cb = QCheckBox(name)
            self.sched_day_checks[i] = cb
            row4.addWidget(cb)

        # 每月的日期选择
        self.sched_month_day_combo = QComboBox()
        self.sched_month_day_combo.addItem('每月1日', 1)
        for d in range(2, 32):
            self.sched_month_day_combo.addItem(f'每月{d}日', d)
        self.sched_month_day_combo.addItem('每月最后一天', 32)
        self.sched_month_day_combo.setVisible(False)
        row4.addWidget(self.sched_month_day_combo)

        row4.addStretch()
        form_layout.addLayout(row4)

        row5 = QHBoxLayout()
        row5.addWidget(QLabel('关联书签：'))
        self.sched_bookmark_list = QTableWidget()
        self.sched_bookmark_list.setColumnCount(2)
        self.sched_bookmark_list.setHorizontalHeaderLabels(['书签名称', 'URL'])
        self.sched_bookmark_list.horizontalHeader().setStretchLastSection(True)
        self.sched_bookmark_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.sched_bookmark_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sched_bookmark_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.sched_bookmark_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sched_bookmark_list.verticalHeader().setVisible(False)
        self.sched_bookmark_list.setMaximumHeight(180)
        row5.addWidget(self.sched_bookmark_list)
        form_layout.addLayout(row5)

        btn_row = QHBoxLayout()
        btn_save = QPushButton('保存')
        btn_save.clicked.connect(self._on_sched_form_save)
        btn_cancel = QPushButton('取消')
        btn_cancel.clicked.connect(self._hide_sched_form)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        form_layout.addLayout(btn_row)

        self._sched_edit_id = None
        parent_layout.addWidget(self.sched_form)
        self._on_sched_repeat_changed()

    def _on_sched_repeat_changed(self, *args):
        val = self.sched_repeat_group.checkedButton()
        if val:
            rt = [k for k, v in self.sched_repeat_radios.items() if v == val][0]
        else:
            rt = 'daily'

        # 每周：显示星期选择
        show_weekdays = (rt == 'weekly')
        self._sched_repeat_day_label.setVisible(show_weekdays)
        for cb in self.sched_day_checks.values():
            cb.setVisible(show_weekdays)

        # 每月：显示日期选择
        show_monthly = (rt == 'monthly')
        self.sched_month_day_combo.setVisible(show_monthly)

        if not show_weekdays and not show_monthly:
            self._sched_repeat_day_label.setVisible(False)

    def _show_sched_form(self, schedule=None):
        self._sched_edit_id = schedule['id'] if schedule else None
        self._sched_form_title.setText('编辑定时任务' if schedule else '新建定时任务')

        self.sched_bookmark_list.setRowCount(0)
        self._sched_bookmark_ids = {}
        all_bookmarks = BookmarkRepo.get_all()
        for idx, bm in enumerate(all_bookmarks):
            self.sched_bookmark_list.insertRow(idx)
            self.sched_bookmark_list.setItem(idx, 0, QTableWidgetItem(bm['title']))
            url_item = QTableWidgetItem(bm['url'])
            url_item.setToolTip(bm['url'])
            self.sched_bookmark_list.setItem(idx, 1, url_item)
            self._sched_bookmark_ids[idx] = bm['id']

        if schedule:
            self.sched_name_edit.setText(schedule.get('name', ''))
            self.sched_hour_spin.setValue(schedule.get('hour', 9))
            self.sched_minute_spin.setValue(schedule.get('minute', 0))
            rt = schedule.get('repeat_type', 'daily')
            if rt in self.sched_repeat_radios:
                self.sched_repeat_radios[rt].setChecked(True)
            import json
            try:
                days = json.loads(schedule.get('repeat_days', '[]'))
                for v in self.sched_day_checks.values():
                    v.setChecked(False)
                for d in days:
                    if d in self.sched_day_checks:
                        self.sched_day_checks[d].setChecked(True)
                # 每月：设置日期选择
                if days and rt == 'monthly':
                    month_day = days[0] if isinstance(days, list) else days
                    idx = self.sched_month_day_combo.findData(month_day)
                    if idx >= 0:
                        self.sched_month_day_combo.setCurrentIndex(idx)
            except (json.JSONDecodeError, TypeError):
                pass
            associated = ScheduleRepo.get_bookmarks(schedule['id'])
            associated_ids = {b['id'] for b in associated}
            for idx, bm_id in self._sched_bookmark_ids.items():
                if bm_id in associated_ids:
                    self.sched_bookmark_list.selectRow(idx)
        else:
            self.sched_name_edit.clear()
            self.sched_hour_spin.setValue(9)
            self.sched_minute_spin.setValue(0)
            self.sched_repeat_radios['daily'].setChecked(True)
            for v in self.sched_day_checks.values():
                v.setChecked(False)
        self.sched_form.show()
        self._on_sched_repeat_changed()

    def _hide_sched_form(self):
        self.sched_form.hide()
        self._sched_edit_id = None

    def _on_sched_form_save(self):
        name = self.sched_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, '输入不完整', '任务名称不能为空')
            return
        hour = self.sched_hour_spin.value()
        minute = self.sched_minute_spin.value()
        checked = self.sched_repeat_group.checkedButton()
        rt = [k for k, v in self.sched_repeat_radios.items() if v == checked][0] if checked else 'daily'
        import json
        if rt == 'monthly':
            repeat_days = json.dumps([self.sched_month_day_combo.currentData()])
        else:
            repeat_days = json.dumps([i for i, v in self.sched_day_checks.items() if v.isChecked()])
        selected_rows = set()
        for item in self.sched_bookmark_list.selectedItems():
            selected_rows.add(item.row())
        bookmark_ids = [self._sched_bookmark_ids[r] for r in selected_rows if r in self._sched_bookmark_ids]
        if self._sched_edit_id:
            ScheduleEngine.update_schedule(self._sched_edit_id, name=name, hour=hour,
                                           minute=minute, repeat_type=rt,
                                           repeat_days=repeat_days)
            ScheduleRepo.set_bookmarks(self._sched_edit_id, bookmark_ids)
        else:
            ScheduleEngine.add_schedule(name, hour, minute, rt,
                                        repeat_days=repeat_days, bookmark_ids=bookmark_ids)
        ScheduleEngine().reload()
        self._hide_sched_form()
        self._load_schedule_list()

    def _load_schedule_list(self):
        self.schedule_table.setRowCount(0)
        schedules = ScheduleRepo.get_all()
        repeat_labels = {
            'once': '仅一次', 'daily': '每天', 'weekdays': '每个工作日',
            'weekly': '每周', 'monthly': '每月',
        }
        for s in schedules:
            row = self.schedule_table.rowCount()
            self.schedule_table.insertRow(row)
            time_str = f"{s['hour']:02d}:{s['minute']:02d}"
            repeat_str = repeat_labels.get(s['repeat_type'], s['repeat_type'])
            if s['repeat_type'] == 'monthly':
                import json
                try:
                    days = json.loads(s.get('repeat_days', '[]'))
                    day = days[0] if days else 1
                    if day == 32:
                        repeat_str = '每月最后一天'
                    else:
                        repeat_str = f'每月{day}日'
                except (json.JSONDecodeError, TypeError, IndexError):
                    pass
            active_str = '启用' if s['is_active'] else '禁用'
            self.schedule_table.setItem(row, 0, QTableWidgetItem(s['name']))
            self.schedule_table.setItem(row, 1, QTableWidgetItem(time_str))
            self.schedule_table.setItem(row, 2, QTableWidgetItem(repeat_str))
            self.schedule_table.setItem(row, 3, QTableWidgetItem(active_str))
            self.schedule_table.item(row, 0).setData(Qt.UserRole, s['id'])

    def _on_schedule_add(self):
        self._show_sched_form()

    def _on_schedule_edit(self):
        row = self.schedule_table.currentRow()
        if row < 0:
            return
        sid = self.schedule_table.item(row, 0).data(Qt.UserRole)
        sched = ScheduleRepo.get_by_id(sid)
        if sched:
            self._show_sched_form(sched)

    def _on_schedule_delete(self):
        row = self.schedule_table.currentRow()
        if row < 0:
            return
        sid = self.schedule_table.item(row, 0).data(Qt.UserRole)
        if QMessageBox.question(self, '确认删除', '确定要删除这个定时任务吗？') == QMessageBox.Yes:
            ScheduleEngine.delete_schedule(sid)
            self._load_schedule_list()

    def _on_schedule_toggle(self):
        row = self.schedule_table.currentRow()
        if row < 0:
            return
        sid = self.schedule_table.item(row, 0).data(Qt.UserRole)
        sched = ScheduleRepo.get_by_id(sid)
        if sched:
            ScheduleEngine.toggle_schedule(sid, not sched['is_active'])
            self._load_schedule_list()

    def _setup_pool_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        toolbar = QWidget()
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(4)
        btn_add = QPushButton('+ 新建池')
        btn_add.clicked.connect(self._on_pool_create)
        btn_del = QPushButton('删除池')
        btn_del.clicked.connect(self._on_pool_delete)
        btn_active = QPushButton('设为活跃')
        btn_active.clicked.connect(self._on_pool_set_active)
        tb_layout.addWidget(btn_add)
        tb_layout.addWidget(btn_del)
        tb_layout.addWidget(btn_active)
        tb_layout.addStretch()
        layout.addWidget(toolbar)

        self.pool_table = QTableWidget()
        self.pool_table.setColumnCount(3)
        self.pool_table.setHorizontalHeaderLabels(['池名称', '书签数', '活跃'])
        self.pool_table.horizontalHeader().setStretchLastSection(True)
        self.pool_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.pool_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pool_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pool_table.verticalHeader().setVisible(False)
        layout.addWidget(self.pool_table)

        self.notebook.addTab(tab, '随机池')

    def _load_pool_list(self):
        self.pool_table.setRowCount(0)
        pools = RandomWalker.get_all_pools()
        for p in pools:
            row = self.pool_table.rowCount()
            self.pool_table.insertRow(row)
            bookmarks = RandomWalker.get_pool_bookmarks(p['id'])
            active_str = '✓' if p['is_active'] else ''
            self.pool_table.setItem(row, 0, QTableWidgetItem(p['name']))
            self.pool_table.setItem(row, 1, QTableWidgetItem(str(len(bookmarks))))
            self.pool_table.setItem(row, 2, QTableWidgetItem(active_str))
            self.pool_table.item(row, 0).setData(Qt.UserRole, p['id'])

    def _on_pool_create(self):
        name, ok = QInputDialog.getText(self, '新建随机池', '请输入池名称：')
        if ok and name.strip():
            RandomWalker.create_pool(name.strip())
            self._on_pool_changed()

    def _on_pool_delete(self):
        row = self.pool_table.currentRow()
        if row < 0:
            return
        if QMessageBox.question(self, '确认删除', '确定要删除这个随机漫步池吗？') == QMessageBox.Yes:
            pid = self.pool_table.item(row, 0).data(Qt.UserRole)
            RandomWalker.delete_pool(pid)
            self._on_pool_changed()

    def _on_pool_set_active(self):
        row = self.pool_table.currentRow()
        if row < 0:
            return
        pid = self.pool_table.item(row, 0).data(Qt.UserRole)
        RandomWalker.set_active_pool(pid)
        self._on_pool_changed()

    def _on_pool_changed(self):
        self._load_pool_list()
        if hasattr(self, 'random_walk_bar'):
            self.random_walk_bar.refresh()
        if hasattr(self, 'bookmark_list'):
            self.bookmark_list.refresh_pools()
        if hasattr(self, 'folder_tree'):
            self.folder_tree.refresh_pool_checkboxes()

    def _setup_trash_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        toolbar = QWidget()
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(4)
        btn_restore = QPushButton('恢复')
        btn_restore.clicked.connect(self._on_trash_restore)
        btn_perma = QPushButton('彻底删除')
        btn_perma.clicked.connect(self._on_trash_permanently_delete)
        btn_empty = QPushButton('清空回收站')
        btn_empty.clicked.connect(self._on_trash_empty)
        tb_layout.addWidget(btn_restore)
        tb_layout.addWidget(btn_perma)
        tb_layout.addWidget(btn_empty)
        tb_layout.addStretch()
        layout.addWidget(toolbar)

        self.trash_table = QTableWidget()
        self.trash_table.setColumnCount(4)
        self.trash_table.setHorizontalHeaderLabels(['标题', '网址', '删除时间', '原文件夹'])
        self.trash_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.trash_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.trash_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.trash_table.setColumnWidth(2, 150)
        self.trash_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.trash_table.setColumnWidth(3, 100)
        self.trash_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.trash_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.trash_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.trash_table.verticalHeader().setVisible(False)
        layout.addWidget(self.trash_table)

        self.notebook.addTab(tab, '回收站')

    def _load_trash_list(self):
        from core.bookmark_manager import BookmarkManager
        from data.folder_repo import FolderRepo
        self.trash_table.setRowCount(0)
        deleted = BookmarkManager.get_deleted()
        for bm in deleted:
            row = self.trash_table.rowCount()
            self.trash_table.insertRow(row)
            self.trash_table.setItem(row, 0, QTableWidgetItem(bm['title']))
            self.trash_table.setItem(row, 1, QTableWidgetItem(bm['url']))
            deleted_at = (bm.get('deleted_at') or '').replace('T', ' ')[:16]
            self.trash_table.setItem(row, 2, QTableWidgetItem(deleted_at))
            folder_name = ''
            if bm.get('folder_id'):
                folder = FolderRepo.get_by_id(bm['folder_id'])
                if folder:
                    folder_name = folder['name']
            self.trash_table.setItem(row, 3, QTableWidgetItem(folder_name))
            self.trash_table.item(row, 0).setData(Qt.UserRole, bm['id'])

    def _on_trash_restore(self):
        selected = self._get_trash_selected_ids()
        if not selected:
            return
        from core.bookmark_manager import BookmarkManager
        for bm_id in selected:
            BookmarkManager.restore_bookmark(bm_id)
        self._load_trash_list()
        if hasattr(self, 'bookmark_list'):
            self.bookmark_list._refresh()

    def _on_trash_permanently_delete(self):
        selected = self._get_trash_selected_ids()
        if not selected:
            return
        if QMessageBox.question(self, '确认永久删除', 
            f'确定要永久删除选中的 {len(selected)} 个书签吗？此操作不可撤销！') == QMessageBox.Yes:
            from core.bookmark_manager import BookmarkManager
            for bm_id in selected:
                BookmarkManager.permanently_delete(bm_id)
            self._load_trash_list()

    def _on_trash_empty(self):
        if QMessageBox.question(self, '确认清空', 
            '确定要清空回收站吗？所有已删除的书签将被永久删除且不可恢复！') == QMessageBox.Yes:
            from core.bookmark_manager import BookmarkManager
            BookmarkManager.empty_trash()
            self._load_trash_list()

    def _get_trash_selected_ids(self):
        ids = []
        for idx in self.trash_table.selectionModel().selectedRows():
            item = self.trash_table.item(idx.row(), 0)
            if item:
                bm_id = item.data(Qt.UserRole)
                if bm_id:
                    ids.append(bm_id)
        return ids

    def refresh_trash(self):
        self._load_trash_list()

    def _setup_random_walk_bar(self):
        self.random_walk_bar = RandomWalkBar(on_pool_changed=self._on_pool_changed)
        self.centralWidget().layout().addWidget(self.random_walk_bar)

    def _on_folder_selected(self, folder_id):
        self.bookmark_list.set_folder(folder_id)

    def _on_search_results(self, results):
        self.notebook.setCurrentIndex(0)
        self.bookmark_list.show_search_results(results)

    def _on_import(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, '导入加密备份', '', 'LinkVault 备份 (*.linkvault)')
        if not filepath:
            return
        password, ok = QInputDialog.getText(self, '输入密码', '请输入备份密码：', echo=QLineEdit.Password)
        if not ok or not password:
            return
        if QMessageBox.question(self, '确认导入', '导入将合并备份中的数据，确定继续吗？') != QMessageBox.Yes:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._worker = _BackupWorker(self)
        self._worker.finished.connect(self._on_import_finished)
        self._worker.error.connect(self._on_backup_error)
        self._worker.run_import(filepath, password)

    def _on_import_finished(self, action):
        QApplication.restoreOverrideCursor()
        self.folder_tree.load_tree()
        self.bookmark_list.load_all()
        QMessageBox.information(self, '导入成功', '备份已成功导入')

    def _on_import_browser_bookmarks(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, '导入浏览器收藏夹', '', 'HTML 文件 (*.html *.htm)')
        if not filepath:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._worker = _BackupWorker(self)
        self._worker.finished.connect(self._on_import_browser_bookmarks_finished)
        self._worker.error.connect(self._on_backup_error)
        self._worker.run_import_browser_bookmarks(filepath)

    def _on_import_browser_bookmarks_finished(self, result):
        QApplication.restoreOverrideCursor()
        _, imported, skipped = result
        self.folder_tree.load_tree()
        self.bookmark_list.load_all()
        msg = f'导入完成！\n成功导入 {imported} 个书签'
        if skipped > 0:
            msg += f'\n跳过 {skipped} 个已存在的书签'
        QMessageBox.information(self, '导入成功', msg)

    def _on_backup_error(self, error_msg):
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, '操作失败', f'操作过程中发生错误：{error_msg}')

    def _on_export(self):
        from ui_qt.dialogs.settings_dialog import BackupFilterDialog
        dlg = BackupFilterDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        folder_ids, tag_names = dlg.get_selection()

        filepath, _ = QFileDialog.getSaveFileName(
            self, '导出加密备份', '', 'LinkVault 备份 (*.linkvault)')
        if not filepath:
            return
        password, ok = QInputDialog.getText(self, '设置密码', '请设置备份密码：', echo=QLineEdit.Password)
        if not ok or not password:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._worker = _BackupWorker(self)
        self._worker.finished.connect(self._on_export_finished)
        self._worker.error.connect(self._on_backup_error)
        self._worker.run_export_linkvault(filepath, password, folder_ids or None, tag_names or None)

    def _on_export_finished(self, action):
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, '导出成功', '备份已成功导出')

    def _on_export_html(self):
        from ui_qt.dialogs.settings_dialog import BackupFilterDialog
        dlg = BackupFilterDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        folder_ids, tag_names = dlg.get_selection()

        filepath, _ = QFileDialog.getSaveFileName(
            self, '导出 HTML 书签', '', 'HTML 书签文件 (*.html)')
        if not filepath:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._worker = _BackupWorker(self)
        self._worker.finished.connect(self._on_export_html_finished)
        self._worker.error.connect(self._on_backup_error)
        self._worker.run_export_html(filepath, folder_ids or None, tag_names or None)

    def _on_export_html_finished(self, action):
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, '导出成功', '书签已成功导出为 HTML')

    def _on_settings(self):
        from ui_qt.dialogs.settings_dialog import SettingsDialog
        SettingsDialog(self, app=self._app).exec()

    def closeEvent(self, event):
        if self._app.tray_icon:
            self.hide()
            event.ignore()
        else:
            self._app.quit_app()

    def refresh_all(self):
        self.folder_tree.load_tree()
        self.bookmark_list.load_all()
        if hasattr(self, 'random_walk_bar'):
            self.random_walk_bar.refresh()
        self._load_schedule_list()
        self._load_pool_list()