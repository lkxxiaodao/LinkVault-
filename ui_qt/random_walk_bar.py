from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QPushButton, QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from core.random_walker import RandomWalker


class RandomWalkBar(QWidget):
    def __init__(self, parent=None, on_pool_changed=None):
        super().__init__(parent)
        self._pools = []
        self._on_pool_changed = on_pool_changed
        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        layout.addWidget(QLabel('🎲 随机漫步'))

        self.pool_combo = QComboBox()
        self.pool_combo.setMinimumWidth(160)
        self.pool_combo.currentTextChanged.connect(self._on_pool_selected)
        layout.addWidget(self.pool_combo)

        btn = QPushButton('漫步')
        btn.clicked.connect(self._on_walk)
        layout.addWidget(btn)

        layout.addStretch()

    def _on_pool_selected(self, name):
        for p in self._pools:
            if p['name'] == name:
                if not p['is_active']:
                    RandomWalker.set_active_pool(p['id'])
                break
        if self._on_pool_changed:
            self._on_pool_changed()

    def _on_walk(self):
        result = RandomWalker.walk()
        if result is None:
            QMessageBox.information(self, '随机漫步', '没有活跃的随机池或池中没有书签。\n请先在"随机池"标签页中管理随机池并添加书签。')

    def refresh(self):
        self._pools = RandomWalker.get_all_pools()
        current = self.pool_combo.currentText()
        self.pool_combo.blockSignals(True)
        self.pool_combo.clear()
        for p in self._pools:
            self.pool_combo.addItem(p['name'])
        active = RandomWalker.get_active_pool()
        if active:
            self.pool_combo.setCurrentText(active['name'])
        elif self._pools:
            self.pool_combo.setCurrentIndex(0)
        else:
            if current:
                self.pool_combo.setCurrentText(current)
        self.pool_combo.blockSignals(False)