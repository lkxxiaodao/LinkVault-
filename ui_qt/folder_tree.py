from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QMessageBox, QFrame, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QBrush, QColor
from core.folder_manager import FolderManager


class FolderTree(QWidget):
    folder_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_folder_id = None
        self._all_item = None
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
        del_btn = QPushButton('- 删除')
        del_btn.clicked.connect(self._on_delete_folder)
        tb_layout.addWidget(self.add_btn)
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
        self.tree.setHeaderHidden(True)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.itemSelectionChanged.connect(self._on_select)
        self.tree.clicked.connect(self._on_clicked)
        layout.addWidget(self.tree)

    def _toggle_form(self):
        if self.form_frame.isVisible():
            self._hide_form()
            return
        self.name_edit.clear()
        self.form_frame.show()
        self.name_edit.setFocus()

    def _hide_form(self):
        self.form_frame.hide()
        self.name_edit.clear()

    def _on_form_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, '输入不完整', '文件夹名称不能为空')
            return
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
        self._all_item.setForeground(0, QBrush(QColor('#1976D2')))
        roots = FolderManager.get_roots()
        for folder in roots:
            self._insert_folder(self.tree, folder)
        self.tree.expandAll()
        self.tree.setCurrentItem(self._all_item)

    def _insert_folder(self, parent, folder):
        item = QTreeWidgetItem(parent)
        item.setText(0, folder['name'])
        item.setData(0, Qt.UserRole, folder['id'])
        children = FolderManager.get_children(folder['id'])
        for child in children:
            self._insert_folder(item, child)
        return item

    def _on_select(self):
        selected = self.tree.selectedItems()
        if selected:
            self._selected_folder_id = selected[0].data(0, Qt.UserRole)
            self.folder_selected.emit(self._selected_folder_id)

    def _on_clicked(self, index):
        item = self.tree.itemAt(index)
        if item is None:
            self.tree.clearSelection()
            self._selected_folder_id = None
            self.folder_selected.emit(None)

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