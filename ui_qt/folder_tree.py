from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QMessageBox, QFrame, QAbstractItemView, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from core.folder_manager import FolderManager
from core.random_walker import RandomWalker
from data.pool_repo import PoolRepo
from data.folder_repo import FolderRepo


class FolderTree(QWidget):
    folder_selected = Signal(object)
    pool_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_folder_id = None
        self._all_item = None
        self._editing_folder_id = None
        self._updating_checkboxes = False
        self._setup_ui()
        self.load_tree()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        toolbar = QWidget()
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(4)
        self.add_btn = QPushButton('+ 文件夹')
        self.add_btn.clicked.connect(self._toggle_form)
        rename_btn = QPushButton('重命名')
        rename_btn.clicked.connect(self._on_rename_folder)
        del_btn = QPushButton('- 删除')
        del_btn.clicked.connect(self._on_delete_folder)
        tb_layout.addWidget(self.add_btn)
        tb_layout.addWidget(rename_btn)
        tb_layout.addWidget(del_btn)
        tb_layout.addStretch()
        layout.addWidget(toolbar)

        self.form_frame = QFrame()
        self.form_frame.setFrameStyle(QFrame.StyledPanel)
        form_layout = QHBoxLayout(self.form_frame)
        form_layout.setContentsMargins(4, 4, 4, 4)
        form_layout.setSpacing(4)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText('文件夹名称')
        self.name_edit.returnPressed.connect(self._on_form_save)
        form_layout.addWidget(self.name_edit)
        btn_save = QPushButton('保存')
        btn_save.clicked.connect(self._on_form_save)
        form_layout.addWidget(btn_save)
        btn_cancel = QPushButton('取消')
        btn_cancel.clicked.connect(self._hide_form)
        form_layout.addWidget(btn_cancel)
        self.form_frame.hide()
        layout.addWidget(self.form_frame)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.itemSelectionChanged.connect(self._on_select)
        self.tree.clicked.connect(self._on_clicked)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tree.header().resizeSection(1, 30)
        self.tree.setIndentation(20)
        # 勾选框样式适配深色主题
        self.tree.setStyleSheet("""
            QTreeWidget::indicator {
                width: 16px;
                height: 16px;
            }
            QTreeWidget::indicator:unchecked {
                background-color: #3a3a3a;
                border: 2px solid #555555;
                border-radius: 3px;
            }
            QTreeWidget::indicator:checked {
                background-color: #90caf9;
                border: 2px solid #64b5f6;
                border-radius: 3px;
            }
            QTreeWidget::indicator:indeterminate {
                background-color: #5a5a5a;
                border: 2px solid #64b5f6;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.tree)

    def _toggle_form(self):
        if self.form_frame.isVisible():
            self._hide_form()
            return
        self._editing_folder_id = None
        self.name_edit.clear()
        self.form_frame.show()
        self.name_edit.setFocus()

    def _hide_form(self):
        self.form_frame.hide()
        self.name_edit.clear()
        self._editing_folder_id = None

    def _on_form_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, '输入不完整', '文件夹名称不能为空')
            return
        if self._editing_folder_id is not None:
            FolderManager.update_folder(self._editing_folder_id, name=name)
        else:
            selected = self.tree.selectedItems()
            parent_id = None
            if selected:
                parent_id = selected[0].data(0, Qt.UserRole)
            FolderManager.create_folder(name, parent_id)
        self._hide_form()
        self.load_tree()

    def load_tree(self):
        self.tree.clear()
        self._all_item = QTreeWidgetItem(self.tree)
        self._all_item.setText(0, '📁 全部书签')
        self._all_item.setData(0, Qt.UserRole, None)
        font = self._all_item.font(0)
        font.setBold(True)
        self._all_item.setFont(0, font)
        self._all_item.setForeground(0, QBrush(QColor('#64b5f6')))
        roots = FolderManager.get_roots()
        for folder in roots:
            self._insert_folder(self.tree, folder)
        self.tree.expandAll()
        self.tree.setCurrentItem(self._all_item)
        self._refresh_pool_checkboxes()

    def _insert_folder(self, parent, folder):
        item = QTreeWidgetItem(parent)
        item.setText(0, folder['name'])
        item.setData(0, Qt.UserRole, folder['id'])
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(1, Qt.Unchecked)
        children = FolderManager.get_children(folder['id'])
        for child in children:
            self._insert_folder(item, child)
        return item

    def _on_item_changed(self, item, column):
        if self._updating_checkboxes:
            return
        if column != 1:
            return
        folder_id = item.data(0, Qt.UserRole)
        if folder_id is None:
            return
        active = RandomWalker.get_active_pool()
        if not active:
            QMessageBox.information(self.window(), '提示', '请先在底部随机漫步栏选择或创建一个池')
            self._updating_checkboxes = True
            item.setCheckState(1, Qt.Unchecked)
            self._updating_checkboxes = False
            return
        state = item.checkState(1)
        if state == Qt.Checked:
            RandomWalker.add_folder_to_pool(active['id'], folder_id)
        else:
            RandomWalker.remove_folder_from_pool(active['id'], folder_id)
        self.pool_changed.emit()

    def _refresh_pool_checkboxes(self):
        self._updating_checkboxes = True
        active = RandomWalker.get_active_pool()
        if active:
            pool_bm_ids = PoolRepo.get_bookmark_ids_set(active['id'])
            bm_folder_map = FolderRepo.get_all_bookmark_folder_ids()
            all_folders = FolderRepo.get_all()
            # 预计算每个文件夹对应的书签 ID 集合（含子文件夹）
            self._folder_bm_cache = {}
            for f in all_folders:
                descendant_ids = FolderRepo.get_descendant_folder_ids([f['id']], all_folders)
                self._folder_bm_cache[f['id']] = {
                    bm_id for bm_id, fid in bm_folder_map.items()
                    if fid in descendant_ids
                }
        else:
            pool_bm_ids = set()
            self._folder_bm_cache = {}

        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            self._refresh_item_checkbox(item, pool_bm_ids)
        self._updating_checkboxes = False

    def _refresh_item_checkbox(self, item, pool_bm_ids):
        folder_id = item.data(0, Qt.UserRole)
        if folder_id is not None and pool_bm_ids:
            folder_bms = self._folder_bm_cache.get(folder_id, set())
            if not folder_bms:
                item.setCheckState(1, Qt.Unchecked)
            elif folder_bms.issubset(pool_bm_ids):
                item.setCheckState(1, Qt.Checked)
            elif folder_bms & pool_bm_ids:
                item.setCheckState(1, Qt.PartiallyChecked)
            else:
                item.setCheckState(1, Qt.Unchecked)
        for i in range(item.childCount()):
            self._refresh_item_checkbox(item.child(i), pool_bm_ids)

    def refresh_pool_checkboxes(self):
        """外部调用：刷新所有文件夹的勾选状态"""
        self._refresh_pool_checkboxes()

    def _on_select(self):
        selected = self.tree.selectedItems()
        if selected:
            self._selected_folder_id = selected[0].data(0, Qt.UserRole)
            self.folder_selected.emit(self._selected_folder_id)

    def _on_clicked(self, index):
        item = self.tree.itemFromIndex(index)
        if item is None:
            self.tree.clearSelection()
            self._selected_folder_id = None
            self.folder_selected.emit(None)

    def _on_rename_folder(self):
        selected = self.tree.selectedItems()
        if not selected:
            QMessageBox.information(self, '提示', '请先选择要重命名的文件夹')
            return
        item = selected[0]
        folder_id = item.data(0, Qt.UserRole)
        if folder_id is None:
            QMessageBox.information(self, '提示', '不能重命名"全部书签"')
            return
        self._editing_folder_id = folder_id
        self.name_edit.setText(item.text(0))
        self.form_frame.show()
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def _on_delete_folder(self):
        selected = self.tree.selectedItems()
        if not selected:
            return
        item = selected[0]
        folder_id = item.data(0, Qt.UserRole)
        if folder_id is None:
            return
        FolderManager.delete_folder(folder_id)
        self._selected_folder_id = None
        self.folder_selected.emit(None)
        self.load_tree()