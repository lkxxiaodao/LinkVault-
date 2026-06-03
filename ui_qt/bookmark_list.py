import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLineEdit, QComboBox, QLabel, QFrame,
    QMessageBox, QAbstractItemView, QMenu, QApplication, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QClipboard
from core.bookmark_manager import BookmarkManager
from core.random_walker import RandomWalker
from infra.browser_launcher import BrowserLauncher


class BookmarkList(QWidget):
    def __init__(self, parent=None, on_refresh_pools=None):
        super().__init__(parent)
        self._current_folder_id = None
        self._search_mode = False
        self._search_results = None
        self._editing_bookmark_id = None
        self._on_refresh_pools = on_refresh_pools
        self._installed_browsers = {}
        self._setup_ui()
        self._load_bookmarks()
        self._refresh_tag_filter_bar()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        toolbar = QWidget()
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(4)
        self.add_btn = QPushButton('+ 添加书签')
        self.add_btn.clicked.connect(self._toggle_add_form)
        btn_edit = QPushButton('编辑')
        btn_edit.clicked.connect(self._on_edit)
        btn_del = QPushButton('删除')
        btn_del.clicked.connect(self._on_delete)
        btn_open = QPushButton('打开')
        btn_open.clicked.connect(self._on_open)
        tb_layout.addWidget(self.add_btn)
        tb_layout.addWidget(btn_edit)
        tb_layout.addWidget(btn_del)
        tb_layout.addWidget(btn_open)
        tb_layout.addStretch()
        self.batch_move_btn = QPushButton('批量移动')
        self.batch_move_btn.clicked.connect(self._on_batch_move)
        self.batch_tag_btn = QPushButton('批量标签')
        self.batch_tag_btn.clicked.connect(self._on_batch_tag)
        self.batch_browser_btn = QPushButton('批量浏览器')
        self.batch_browser_btn.clicked.connect(self._on_batch_browser)
        self.batch_del_btn = QPushButton('批量删除')
        self.batch_del_btn.clicked.connect(self._on_batch_delete)
        tb_layout.addWidget(self.batch_move_btn)
        tb_layout.addWidget(self.batch_tag_btn)
        tb_layout.addWidget(self.batch_browser_btn)
        tb_layout.addWidget(self.batch_del_btn)
        layout.addWidget(toolbar)

        sort_bar = QWidget()
        sort_layout = QHBoxLayout(sort_bar)
        sort_layout.setContentsMargins(0, 0, 0, 0)
        sort_layout.setSpacing(4)
        sort_layout.addWidget(QLabel('排序：'))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(['默认（标题）', '最常打开', '最近打开'])
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        self.reset_stats_btn = QPushButton('重置统计')
        self.reset_stats_btn.clicked.connect(self._on_reset_stats)
        sort_layout.addWidget(self.reset_stats_btn)
        layout.addWidget(sort_bar)

        self._setup_inline_form()
        layout.addWidget(self.form_frame)

        self._setup_tag_filter_bar()
        layout.addWidget(self.tag_filter_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(['标题', '网址', '备注', '标签', '池', '点击次数', '最近打开'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 150)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 90)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 65)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 100)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 130)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table)

    def _setup_inline_form(self):
        self.form_frame = QFrame()
        self.form_frame.setFrameStyle(QFrame.StyledPanel)
        form_layout = QVBoxLayout(self.form_frame)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(6)

        title_label = QLabel('添加书签')
        title_label.setProperty('class', 'h2')
        form_layout.addWidget(title_label)
        self._form_title = title_label

        row1 = QHBoxLayout()
        row1.addWidget(QLabel('网址：'))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText('输入网址')
        self.url_edit.returnPressed.connect(lambda: self.title_edit.setFocus())
        row1.addWidget(self.url_edit)
        form_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel('标题：'))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText('输入标题')
        self.title_edit.returnPressed.connect(self._on_form_save)
        row2.addWidget(self.title_edit)
        form_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel('浏览器：'))
        self.browser_combo = QComboBox()
        self.browser_combo.setMinimumWidth(180)
        self.browser_combo.addItem('系统默认')
        row3.addWidget(self.browser_combo)
        row3.addStretch()
        form_layout.addLayout(row3)

        row_notes = QHBoxLayout()
        row_notes.addWidget(QLabel('备注：'))
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText('最多15字，记录重点内容...')
        self.notes_edit.setMaxLength(15)
        row_notes.addWidget(self.notes_edit)
        form_layout.addLayout(row_notes)

        row_tags = QHBoxLayout()
        row_tags.addWidget(QLabel('标签：'))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText('每个标签最多5字，逗号分隔，如: 工作, 灵感, 待读')
        row_tags.addWidget(self.tags_edit)
        form_layout.addLayout(row_tags)

        btn_row = QHBoxLayout()
        btn_save = QPushButton('保存')
        btn_save.clicked.connect(self._on_form_save)
        btn_cancel = QPushButton('取消')
        btn_cancel.clicked.connect(self._hide_form)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch()
        form_layout.addLayout(btn_row)

        self.form_frame.hide()

    def _toggle_add_form(self):
        if self.form_frame.isVisible():
            self._hide_form()
            return
        self._editing_bookmark_id = None
        self._form_title.setText('添加书签')
        self.title_edit.clear()
        self._refresh_browser_list()
        self.browser_combo.setCurrentIndex(0)
        self._auto_fill_clipboard()
        self.form_frame.show()
        self.url_edit.setFocus()

    def _auto_fill_clipboard(self):
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if text and re.match(r'^https?://', text.strip()):
                self.url_edit.setText(text.strip())
                self.title_edit.setFocus()
        except Exception:
            pass

    def _hide_form(self):
        self.form_frame.hide()
        self._editing_bookmark_id = None
        self.title_edit.clear()
        self.url_edit.clear()
        self.notes_edit.clear()
        self.tags_edit.clear()

    def _setup_tag_filter_bar(self):
        from PySide6.QtWidgets import QScrollArea
        self.tag_filter_bar = QWidget()
        self.tag_filter_bar.setMaximumHeight(36)
        self.tag_filter_layout = QHBoxLayout(self.tag_filter_bar)
        self.tag_filter_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_filter_layout.setSpacing(4)
        self.tag_filter_layout.addWidget(QLabel('标签筛选：'))
        self.tag_filter_bar.hide()

    def _refresh_tag_filter_bar(self):
        while self.tag_filter_layout.count() > 1:
            item = self.tag_filter_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        all_tags = BookmarkManager.get_all_tags()
        if not all_tags:
            self.tag_filter_bar.hide()
            return
        self.tag_filter_bar.show()
        for t in all_tags:
            btn = QPushButton(f'{t["name"]} ({t["cnt"]})')
            btn.setMaximumHeight(24)
            btn.setStyleSheet('font-size: 11px; padding: 2px 8px;')
            btn.clicked.connect(lambda checked, name=t['name']: self._filter_by_tag(name))
            self.tag_filter_layout.addWidget(btn)
        clear_btn = QPushButton('✕ 清除')
        clear_btn.setMaximumHeight(24)
        clear_btn.setStyleSheet('font-size: 11px; padding: 2px 8px; color: #888;')
        clear_btn.clicked.connect(self._clear_filter)
        self.tag_filter_layout.addWidget(clear_btn)
        self.tag_filter_layout.addStretch()

    def _on_form_save(self):
        title = self.title_edit.text().strip()
        url = self.url_edit.text().strip()
        if not title or not url:
            QMessageBox.warning(self, '输入不完整', '标题和网址不能为空')
            return
        browser_path = self._get_browser_path()
        notes = self.notes_edit.text().strip()
        if self._editing_bookmark_id:
            BookmarkManager.update_bookmark(self._editing_bookmark_id, title=title, url=url,
                                            folder_id=None, default_browser=browser_path, notes=notes)
            bookmark_id = self._editing_bookmark_id
        else:
            bookmark_id = BookmarkManager.add_bookmark(title, url, self._current_folder_id, browser_path, notes)
        tag_names = [t.strip()[:5] for t in self.tags_edit.text().split(',') if t.strip()]
        BookmarkManager.set_tags(bookmark_id, tag_names)
        self._hide_form()
        self._refresh()
        if self._on_refresh_pools:
            self._on_refresh_pools()

    def _on_cell_clicked(self, row, col):
        if col == 4:
            self._toggle_pool(row)

    def _on_cell_double_clicked(self, row, col):
        if col not in (2, 3, 4):
            self._on_open()

    def _toggle_pool(self, row):
        item = self.table.item(row, 0)
        if not item:
            return
        bookmark_id = item.data(Qt.UserRole)
        if not bookmark_id:
            return
        active = RandomWalker.get_active_pool()
        if not active:
            QMessageBox.information(self, '提示', '请先在底部随机漫步栏选择或创建一个池')
            return
        pool_bookmarks = RandomWalker.get_pool_bookmarks(active['id'])
        in_pool = any(b['id'] == bookmark_id for b in pool_bookmarks)
        if in_pool:
            RandomWalker.remove_from_pool(active['id'], bookmark_id)
        else:
            RandomWalker.add_to_pool(active['id'], bookmark_id)
        self._refresh_pool_column()

    def _is_in_active_pool(self, bookmark_id):
        active = RandomWalker.get_active_pool()
        if not active:
            return False
        bookmarks = RandomWalker.get_pool_bookmarks(active['id'])
        return any(b['id'] == bookmark_id for b in bookmarks)

    def _refresh_pool_column(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                bm_id = item.data(Qt.UserRole)
                in_pool = self._is_in_active_pool(bm_id)
                pool_item = self.table.item(row, 4)
                if pool_item:
                    pool_item.setText('☑' if in_pool else '☐')

    def _on_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        selected_ids = self._get_selected_bookmark_ids()
        if row not in [idx.row() for idx in self.table.selectionModel().selectedRows()]:
            self.table.selectRow(row)
            selected_ids = [self._get_selected_bookmark_id()]
        menu = QMenu(self)
        menu.addAction('打开', self._on_open)
        menu.addAction('复制标题', self._on_copy_title)
        menu.addAction('复制网址', self._on_copy_url)
        menu.addSeparator()
        menu.addAction('编辑', self._on_edit)
        menu.addAction('删除', self._on_delete)
        if len(selected_ids) > 1:
            menu.addSeparator()
            batch_menu = menu.addMenu(f'批量操作 ({len(selected_ids)}个)')
            batch_menu.addAction('批量移动...', self._on_batch_move)
            batch_menu.addAction('批量添加标签...', self._on_batch_tag)
            batch_menu.addAction('批量修改浏览器...', self._on_batch_browser)
            batch_menu.addAction('批量删除', self._on_batch_delete)
        menu.addSeparator()
        tag_menu = menu.addMenu('按标签筛选')
        all_tags = BookmarkManager.get_all_tags()
        if all_tags:
            for t in all_tags:
                action = tag_menu.addAction(f'{t["name"]} ({t["cnt"]})')
                action.setData(t['name'])
                action.triggered.connect(lambda checked, name=t['name']: self._filter_by_tag(name))
        else:
            tag_menu.addAction('(无标签)').setEnabled(False)
        tag_menu.addSeparator()
        clear_action = tag_menu.addAction('清除筛选')
        clear_action.triggered.connect(self._clear_filter)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _on_copy_title(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if item:
            QApplication.clipboard().setText(item.text())

    def _on_copy_url(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 1)
        if item:
            QApplication.clipboard().setText(item.text())

    def _load_bookmarks(self, folder_id=None):
        self.table.setRowCount(0)
        sort_index = self.sort_combo.currentIndex() if hasattr(self, 'sort_combo') else 0
        if sort_index == 1:
            bookmarks = BookmarkManager.get_most_opened()
        elif sort_index == 2:
            bookmarks = BookmarkManager.get_recently_opened()
        elif folder_id is not None:
            bookmarks = BookmarkManager.get_by_folder(folder_id)
        else:
            bookmarks = BookmarkManager.get_all()
        bm_ids = [bm['id'] for bm in bookmarks]
        tags_map = BookmarkManager.get_batch_tags(bm_ids) if bm_ids else {}
        for bm in bookmarks:
            row = self.table.rowCount()
            self.table.insertRow(row)
            in_pool = self._is_in_active_pool(bm['id'])
            title_item = QTableWidgetItem(bm['title'])
            title_item.setData(Qt.UserRole, bm['id'])
            notes = (bm.get('notes') or '').strip()
            title_item.setToolTip(notes if notes else bm['title'])
            self.table.setItem(row, 0, title_item)
            self.table.setItem(row, 1, QTableWidgetItem(bm['url']))
            self.table.setItem(row, 2, QTableWidgetItem(notes))
            bm_tags = tags_map.get(bm['id'], [])
            self.table.setItem(row, 3, QTableWidgetItem(' '.join(bm_tags) if bm_tags else ''))
            self.table.setItem(row, 4, QTableWidgetItem('\u2611' if in_pool else '\u2610'))
            click_count = bm.get('click_count') or 0
            self.table.setItem(row, 5, QTableWidgetItem(str(click_count)))
            last_opened = bm.get('last_opened_at') or ''
            if last_opened:
                last_opened = last_opened.replace('T', ' ')[:16]
            self.table.setItem(row, 6, QTableWidgetItem(last_opened))

    def set_folder(self, folder_id):
        self._current_folder_id = folder_id
        self._search_mode = False
        self._search_results = None
        self._load_bookmarks(folder_id)
        self._refresh_tag_filter_bar()

    def load_all(self):
        self._current_folder_id = None
        self._search_mode = False
        self._search_results = None
        self._load_bookmarks(None)
        self._refresh_tag_filter_bar()

    def show_search_results(self, results):
        if results is None:
            self._search_mode = False
            self._search_results = None
            self._load_bookmarks(self._current_folder_id)
            return
        self._search_mode = True
        self._search_results = results
        self.table.setRowCount(0)
        bm_ids = [bm['id'] for bm in results]
        tags_map = BookmarkManager.get_batch_tags(bm_ids) if bm_ids else {}
        for bm in results:
            row = self.table.rowCount()
            self.table.insertRow(row)
            in_pool = self._is_in_active_pool(bm['id'])
            title_item = QTableWidgetItem(bm['title'])
            title_item.setData(Qt.UserRole, bm['id'])
            notes = (bm.get('notes') or '').strip()
            title_item.setToolTip(notes if notes else bm['title'])
            self.table.setItem(row, 0, title_item)
            self.table.setItem(row, 1, QTableWidgetItem(bm['url']))
            self.table.setItem(row, 2, QTableWidgetItem(notes))
            bm_tags = tags_map.get(bm['id'], [])
            self.table.setItem(row, 3, QTableWidgetItem(' '.join(bm_tags) if bm_tags else ''))
            self.table.setItem(row, 4, QTableWidgetItem('\u2611' if in_pool else '\u2610'))
            click_count = bm.get('click_count') or 0
            self.table.setItem(row, 5, QTableWidgetItem(str(click_count)))
            last_opened = bm.get('last_opened_at') or ''
            if last_opened:
                last_opened = last_opened.replace('T', ' ')[:16]
            self.table.setItem(row, 6, QTableWidgetItem(last_opened))

    def _get_selected_bookmark_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _get_selected_bookmark_ids(self):
        ids = []
        for idx in self.table.selectionModel().selectedRows():
            item = self.table.item(idx.row(), 0)
            if item:
                bm_id = item.data(Qt.UserRole)
                if bm_id:
                    ids.append(bm_id)
        return ids

    def _on_edit(self):
        bookmark_id = self._get_selected_bookmark_id()
        if not bookmark_id:
            return
        bm = BookmarkManager.get_by_id(bookmark_id)
        if not bm:
            return
        self._hide_form()
        self._editing_bookmark_id = bookmark_id
        self._form_title.setText('编辑书签')
        self.title_edit.setText(bm.get('title', ''))
        self.url_edit.setText(bm.get('url', ''))
        self.notes_edit.setText(bm.get('notes', ''))
        tags = BookmarkManager.get_tags(bookmark_id)
        self.tags_edit.setText(', '.join(t['name'] for t in tags) if tags else '')
        self._refresh_browser_list()
        browser_path = bm.get('default_browser', '')
        if browser_path:
            for i in range(self.browser_combo.count()):
                if self.browser_combo.itemData(i) == browser_path:
                    self.browser_combo.setCurrentIndex(i)
                    break
            else:
                self.browser_combo.setCurrentIndex(0)
        else:
            self.browser_combo.setCurrentIndex(0)
        self.form_frame.show()
        self.title_edit.setFocus()

    def _refresh_browser_list(self):
        self._installed_browsers = BrowserLauncher.get_installed_browsers()
        self.browser_combo.clear()
        self.browser_combo.addItem('系统默认', None)
        for name, path in self._installed_browsers.items():
            self.browser_combo.addItem(name, path)

    def _get_browser_path(self):
        return self.browser_combo.currentData()

    def _on_delete(self):
        bookmark_id = self._get_selected_bookmark_id()
        if not bookmark_id:
            return
        if QMessageBox.question(self, '确认删除', '确定要删除这个书签吗？书签将移入回收站，可在回收站中恢复。') == QMessageBox.Yes:
            BookmarkManager.delete_bookmark(bookmark_id)
            self._refresh()

    def _on_batch_move(self):
        ids = self._get_selected_bookmark_ids()
        if not ids:
            QMessageBox.information(self, '提示', '请先选中要移动的书签（Ctrl+点击多选）')
            return
        from core.folder_manager import FolderManager
        folders = FolderManager.get_all()
        if not folders:
            QMessageBox.information(self, '提示', '暂无文件夹，请先创建文件夹')
            return
        folder_names = ['(无/根目录)'] + [f['name'] for f in folders]
        folder_ids = [None] + [f['id'] for f in folders]
        choice, ok = QInputDialog.getItem(self, '批量移动', f'将 {len(ids)} 个书签移动到：', folder_names, 0, False)
        if ok and choice:
            idx = folder_names.index(choice)
            BookmarkManager.batch_move_to_folder(ids, folder_ids[idx])
            self._refresh()

    def _on_batch_tag(self):
        ids = self._get_selected_bookmark_ids()
        if not ids:
            QMessageBox.information(self, '提示', '请先选中要添加标签的书签（Ctrl+点击多选）')
            return
        text, ok = QInputDialog.getText(self, '批量添加标签', f'为 {len(ids)} 个书签添加标签（逗号分隔）：')
        if ok and text.strip():
            tag_names = [t.strip() for t in text.split(',') if t.strip()]
            BookmarkManager.batch_add_tags(ids, tag_names)
            self._refresh()

    def _on_batch_browser(self):
        ids = self._get_selected_bookmark_ids()
        if not ids:
            QMessageBox.information(self, '提示', '请先选中要修改的书签（Ctrl+点击多选）')
            return
        self._refresh_browser_list()
        browsers = ['系统默认'] + list(self._installed_browsers.keys())
        browser_paths = [None] + list(self._installed_browsers.values())
        choice, ok = QInputDialog.getItem(self, '批量修改浏览器', f'将 {len(ids)} 个书签的浏览器设为：', browsers, 0, False)
        if ok and choice:
            idx = browsers.index(choice)
            BookmarkManager.batch_update(ids, default_browser=browser_paths[idx])
            self._refresh()

    def _on_batch_delete(self):
        ids = self._get_selected_bookmark_ids()
        if not ids:
            QMessageBox.information(self, '提示', '请先选中要删除的书签（Ctrl+点击多选）')
            return
        if QMessageBox.question(self, '确认批量删除', f'确定要删除选中的 {len(ids)} 个书签吗？书签将移入回收站，可在回收站中恢复。') == QMessageBox.Yes:
            BookmarkManager.batch_delete(ids)
            self._refresh()

    def _on_open(self):
        bookmark_id = self._get_selected_bookmark_id()
        if bookmark_id:
            BookmarkManager.open_in_browser(bookmark_id)
            self._refresh()

    def _refresh(self):
        if self._search_mode:
            self._search_mode = False
            self._search_results = None
        if self._current_folder_id is not None:
            self._load_bookmarks(self._current_folder_id)
        else:
            self._load_bookmarks(None)
        self._refresh_tag_filter_bar()

    def refresh_pools(self):
        self._refresh_pool_column()

    def _on_sort_changed(self, index):
        self._refresh()

    def _on_reset_stats(self):
        reply = QMessageBox.question(
            self, '重置统计', 
            '确定要重置所有书签的点击统计吗？（点击次数和最近打开时间将被清零）',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            BookmarkManager.reset_stats()
            self._refresh()

    def _filter_by_tag(self, tag_name):
        results = BookmarkManager.search_by_tag(tag_name)
        self._search_mode = True
        self._search_results = results
        self.show_search_results(results)

    def _clear_filter(self):
        self._search_mode = False
        self._search_results = None
        self._load_bookmarks(self._current_folder_id)
        self._refresh_tag_filter_bar()