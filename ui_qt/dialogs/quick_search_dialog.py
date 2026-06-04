from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QApplication, QTreeWidget, QTreeWidgetItem, QSplitter, QWidget,
    QAbstractItemView
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QFont, QBrush, QColor
from core.bookmark_manager import BookmarkManager
from core.folder_manager import FolderManager
from infra.browser_launcher import BrowserLauncher


class QuickSearchDialog(QDialog):
    bookmark_opened = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('LinkVault 快速搜索')
        self.setWindowFlags(
            Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.resize(700, 460)
        self.setMinimumSize(600, 380)
        self._results = []
        self._current_folder_id = None
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._do_search)
        self._setup_ui()
        self._center_on_screen()
        self.finished.connect(self._on_closed)

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
            QLineEdit {
                border: none;
                border-bottom: 1px solid #3d3d3d;
                padding: 10px 14px;
                font-size: 15px;
                background: transparent;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #64b5f6;
            }
            QListWidget {
                border: none;
                font-size: 13px;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 14px;
                border-bottom: 1px solid #2a2a2a;
            }
            QListWidget::item:selected {
                background-color: #1e3a5f;
                color: #e0e0e0;
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
            }
            QTreeWidget {
                border: none;
                border-right: 1px solid #3d3d3d;
                font-size: 13px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 4px 8px;
            }
            QTreeWidget::item:selected {
                background-color: #1e3a5f;
                color: #e0e0e0;
            }
            QTreeWidget::item:hover {
                background-color: #2a2a2a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setFixedHeight(36)
        title_bar.setStyleSheet('background-color: #252525; border-bottom: 1px solid #3d3d3d; border-radius: 8px 8px 0 0;')
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(12, 0, 12, 0)
        title_label = QLabel('LinkVault 快速搜索')
        title_label.setStyleSheet('font-weight: bold; color: #cccccc;')
        tb_layout.addWidget(title_label)
        tb_layout.addStretch()
        hint = QLabel('Esc 关闭 | ↑↓ 导航 | Enter 打开')
        hint.setStyleSheet('color: #888888; font-size: 11px;')
        tb_layout.addWidget(hint)
        layout.addWidget(title_bar)

        self.input = QLineEdit()
        self.input.setPlaceholderText('输入关键词搜索标题、网址、备注、标签...（或直接浏览下方列表）')
        self.input.textChanged.connect(self._on_text_changed)
        self.input.returnPressed.connect(self._on_return)
        layout.addWidget(self.input)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)

        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.folder_tree.itemClicked.connect(self._on_folder_clicked)
        self.folder_tree.setMaximumWidth(220)
        splitter.addWidget(self.folder_tree)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(self._on_item_activated)
        self.result_list.itemClicked.connect(self._on_item_activated)
        right_layout.addWidget(self.result_list)

        self.hint_label = QLabel('输入关键词搜索，或点击左侧文件夹浏览...')
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet('color: #888888; padding: 20px;')
        right_layout.addWidget(self.hint_label)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            center = screen.geometry().center()
            self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)

    def _build_folder_tree(self):
        self.folder_tree.clear()
        all_item = QTreeWidgetItem(self.folder_tree)
        all_item.setText(0, '全部书签')
        all_item.setData(0, Qt.UserRole, None)
        font = all_item.font(0)
        font.setBold(True)
        all_item.setFont(0, font)
        all_item.setForeground(0, QBrush(QColor('#64b5f6')))
        roots = FolderManager.get_roots()
        for folder in roots:
            self._insert_folder(self.folder_tree, folder)
        self.folder_tree.expandAll()
        self.folder_tree.setCurrentItem(all_item)
        self._current_folder_id = None

    def _insert_folder(self, parent, folder):
        item = QTreeWidgetItem(parent)
        item.setText(0, folder['name'])
        item.setData(0, Qt.UserRole, folder['id'])
        children = FolderManager.get_children(folder['id'])
        for child in children:
            self._insert_folder(item, child)
        return item

    def _on_folder_clicked(self, item, col):
        folder_id = item.data(0, Qt.UserRole)
        self._current_folder_id = folder_id
        self.input.clear()
        self._load_folder_bookmarks(folder_id)

    def _load_folder_bookmarks(self, folder_id):
        if folder_id is not None:
            bookmarks = BookmarkManager.get_by_folder(folder_id)
        else:
            bookmarks = BookmarkManager.get_all()
        self._results = bookmarks
        self._render_results()

    def _on_text_changed(self, text):
        if not text.strip():
            self._debounce_timer.stop()
            self._load_folder_bookmarks(self._current_folder_id)
            return
        self._debounce_timer.start(150)

    def _do_search(self):
        query = self.input.text().strip()
        if not query:
            return
        self._results = BookmarkManager.search(query)
        self._render_results()

    def _render_results(self):
        self.result_list.clear()
        if not self._results:
            self.result_list.hide()
            query = self.input.text().strip()
            if query:
                self.hint_label.setText('没有找到匹配的书签')
            else:
                self.hint_label.setText('当前文件夹为空')
            self.hint_label.show()
            return
        self.hint_label.hide()
        self.result_list.show()
        bm_ids = [bm['id'] for bm in self._results]
        tags_map = BookmarkManager.get_batch_tags(bm_ids) if bm_ids else {}
        for bm in self._results:
            tags = tags_map.get(bm['id'], [])
            tag_text = ' | '.join(tags) if tags else ''
            display = bm['title'] or '(无标题)'
            subtitle = bm['url']
            if tag_text:
                subtitle += f'  ·  {tag_text}'
            notes = (bm.get('notes') or '').strip()
            if notes:
                subtitle += f'  ·  {notes}'

            item = QListWidgetItem()
            item.setData(Qt.UserRole, bm)
            item.setText(display + '\n' + subtitle)
            item.setToolTip(bm['url'])
            self.result_list.addItem(item)
        self.result_list.setCurrentRow(0)

    def _on_return(self):
        current = self.result_list.currentItem()
        if current:
            self._open_bookmark(current.data(Qt.UserRole))
        else:
            self._do_search()
            self.result_list.setFocus()

    def _on_item_activated(self, item):
        if item:
            self._open_bookmark(item.data(Qt.UserRole))

    def _open_bookmark(self, bm):
        BrowserLauncher.open_url(bm['url'], bm.get('default_browser'))
        self.bookmark_opened.emit(bm)
        self.accept()

    def _on_closed(self):
        self.input.clear()
        self.result_list.clear()
        self._results = []
        self.hint_label.show()
        self.result_list.hide()

    def show_and_focus(self):
        self._center_on_screen()
        self._build_folder_tree()
        self._load_folder_bookmarks(None)
        self.show()
        self.raise_()
        self.activateWindow()
        self.input.clear()
        self.input.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.reject()
            return
        if event.key() == Qt.Key_Down:
            if self.result_list.count() > 0:
                current = self.result_list.currentRow()
                next_row = min(current + 1, self.result_list.count() - 1)
                self.result_list.setCurrentRow(next_row)
            return
        if event.key() == Qt.Key_Up:
            if self.result_list.count() > 0:
                current = self.result_list.currentRow()
                next_row = max(current - 1, 0)
                self.result_list.setCurrentRow(next_row)
            return
        if not self.input.hasFocus():
            self.input.setFocus()
            self.input.keyPressEvent(event)