from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from core.bookmark_manager import BookmarkManager
from core.url_extractor import UrlExtractor


class SearchBar(QWidget):
    def __init__(self, parent=None, on_results=None):
        super().__init__(parent)
        self.on_results = on_results
        self._url_debounce_timer = QTimer()
        self._url_debounce_timer.setSingleShot(True)
        self._url_debounce_timer.setInterval(500)
        self._url_debounce_timer.timeout.connect(self._check_urls_debounced)
        self._pending_urls = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel('搜索：')
        layout.addWidget(label)

        self.entry = QLineEdit()
        self.entry.setPlaceholderText('搜索标题、网址、备注...')
        self.entry.returnPressed.connect(self._do_search)
        self.entry.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.entry)

        btn = QPushButton('搜索')
        btn.clicked.connect(self._do_search)
        layout.addWidget(btn)

    def _on_text_changed(self, text):
        urls = UrlExtractor.extract(text.strip())
        if urls:
            self._pending_urls = urls
            self._url_debounce_timer.start()

    def _check_urls_debounced(self):
        """防抖后检查新 URL，改用非模态提示"""
        urls = self._pending_urls
        self._pending_urls = []
        for url in urls:
            existing = BookmarkManager.find_by_url(url)
            if not existing:
                if QMessageBox.question(self, '发现新链接', f'是否收藏此链接？\n\n{url}') == QMessageBox.Yes:
                    BookmarkManager.add_bookmark(url.split('//')[-1][:50], url)

    def _do_search(self):
        query = self.entry.text().strip()
        if not query:
            if self.on_results:
                self.on_results(None)
            return
        results = BookmarkManager.search(query)
        if self.on_results:
            self.on_results(results)