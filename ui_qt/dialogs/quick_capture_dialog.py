import re
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
    QPushButton, QComboBox, QApplication
)
from PySide6.QtCore import Qt, QTimer, Signal
from core.bookmark_manager import BookmarkManager
from core.folder_manager import FolderManager
from core.url_extractor import UrlExtractor
from infra.browser_launcher import BrowserLauncher
from ui_qt.preset_tag_bar import PresetTagBar


class QuickCaptureDialog(QDialog):
    """快速捕获书签对话框 - 通过全局快捷键唤出"""

    bookmark_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('快速添加书签 - LinkVault')
        self.setWindowFlags(
            Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.resize(520, 280)
        self._setup_ui()
        self._center_on_screen()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 1px solid #c0c0c0;
                border-radius: 8px;
            }
            QLineEdit {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #1976D2;
            }
            QLabel {
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        title_bar = QHBoxLayout()
        title_label = QLabel('<b>快速添加书签</b>')
        title_label.setStyleSheet('font-size: 14px;')
        title_bar.addWidget(title_label)
        title_bar.addStretch()
        hint = QLabel('Esc 关闭 | Enter 保存')
        hint.setStyleSheet('color: #999; font-size: 11px;')
        title_bar.addWidget(hint)
        layout.addLayout(title_bar)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel('网址：'))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText('输入网址')
        self.url_edit.returnPressed.connect(lambda: self.title_edit.setFocus())
        row1.addWidget(self.url_edit)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel('标题：'))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText('输入标题')
        self.title_edit.returnPressed.connect(self._on_save)
        row2.addWidget(self.title_edit)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel('文件夹：'))
        self.folder_combo = QComboBox()
        self.folder_combo.setMinimumWidth(180)
        self._load_folders()
        row3.addWidget(self.folder_combo)
        row3.addStretch()
        layout.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel('标签：'))
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText('手动输入，逗号分隔，如: 工作, 待读')
        row4.addWidget(self.tags_edit)
        layout.addLayout(row4)

        self.preset_tag_bar = PresetTagBar()
        layout.addWidget(self.preset_tag_bar)

        btn_row = QHBoxLayout()
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: #43a047; font-size: 11px;')
        btn_row.addWidget(self.status_label)
        btn_row.addStretch()
        btn_save = QPushButton('保存')
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._on_save)
        btn_cancel = QPushButton('取消')
        btn_cancel.clicked.connect(self.close)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

    def _load_folders(self):
        self.folder_combo.clear()
        self.folder_combo.addItem('(无)', None)
        roots = FolderManager.get_roots()
        for folder in roots:
            self._add_folder_to_combo(folder, 0)

    def _add_folder_to_combo(self, folder, depth):
        prefix = '  ' * depth + ('└ ' if depth > 0 else '')
        self.folder_combo.addItem(f'{prefix}{folder["name"]}', folder['id'])
        children = FolderManager.get_children(folder['id'])
        for child in children:
            self._add_folder_to_combo(child, depth + 1)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            center = screen.geometry().center()
            self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)

    def show_and_focus(self):
        self._auto_fill_url()
        self.show()
        self.raise_()
        self.activateWindow()
        if self.url_edit.text().strip():
            self.title_edit.setFocus()
        else:
            self.url_edit.setFocus()

    def _auto_fill_url(self):
        self.url_edit.clear()
        self.title_edit.clear()
        self.tags_edit.clear()
        self.preset_tag_bar.clear_selection()
        self.status_label.clear()
        self.folder_combo.setCurrentIndex(0)

        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            urls = UrlExtractor.extract(text.strip())
            if urls:
                self.url_edit.setText(urls[0])
                self.status_label.setText('已从剪贴板填入网址')
                return
            if re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}', text.strip()):
                self.url_edit.setText('https://' + text.strip())
                self.status_label.setText('已从剪贴板填入网址')
                return

    def _on_save(self):
        title = self.title_edit.text().strip()
        url = self.url_edit.text().strip()
        if not url:
            self.status_label.setText('请输入网址')
            self.status_label.setStyleSheet('color: #e53935; font-size: 11px;')
            self.url_edit.setFocus()
            return
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
            self.url_edit.setText(url)
        if not title:
            title = url.split('//')[-1].split('/')[0][:50]
        folder_id = self.folder_combo.currentData()
        existing = BookmarkManager.find_by_url(url)
        if existing:
            self.status_label.setText('该书签已存在')
            self.status_label.setStyleSheet('color: #e53935; font-size: 11px;')
            return
        bookmark_id = BookmarkManager.add_bookmark(title, url, folder_id)
        tag_names = [t.strip()[:5] for t in self.tags_edit.text().split(',') if t.strip()]
        preset_tags = self.preset_tag_bar.get_selected_tags()
        all_tags = list(dict.fromkeys(preset_tags + tag_names))
        if all_tags:
            BookmarkManager.set_tags(bookmark_id, all_tags)
        self.status_label.setText('书签已保存！')
        self.status_label.setStyleSheet('color: #43a047; font-size: 11px;')
        self.bookmark_saved.emit()
        QTimer.singleShot(1500, self.close)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)