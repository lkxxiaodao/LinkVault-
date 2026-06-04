"""预设标签按钮栏 - 用户可点击按钮快速选择/取消标签"""
import json
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QInputDialog, QMessageBox, QLabel
)
from PySide6.QtCore import Signal, Qt
from core.config_manager import ConfigManager

MAX_PRESET_TAGS = 10
CONFIG_KEY = 'preset_tags'


class PresetTagBar(QWidget):
    """预设标签按钮栏，支持多选切换、添加/删除预设标签，有数量上限"""

    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_tags = set()
        self._buttons = {}
        self._setup_ui()
        self._load_presets()

    def _setup_ui(self):
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)

        self._label = QLabel('预设标签：')
        self._layout.addWidget(self._label)

        self._btn_layout = QHBoxLayout()
        self._btn_layout.setSpacing(4)
        self._layout.addLayout(self._btn_layout)

        self._add_btn = QPushButton('+')
        self._add_btn.setFixedSize(26, 26)
        self._add_btn.setToolTip(f'添加预设标签（最多{MAX_PRESET_TAGS}个）')
        self._add_btn.setStyleSheet('font-size: 14px; font-weight: bold;')
        self._add_btn.clicked.connect(self._on_add_preset)
        self._layout.addWidget(self._add_btn)

        self._layout.addStretch()

    def _load_presets(self):
        raw = ConfigManager.get(CONFIG_KEY, '[]')
        try:
            preset_tags = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            preset_tags = []
        for name in preset_tags:
            self._add_button(name)

    def _save_presets(self):
        names = list(self._buttons.keys())
        ConfigManager.set(CONFIG_KEY, json.dumps(names, ensure_ascii=False))

    def _add_button(self, name):
        if name in self._buttons:
            return
        btn = QPushButton(name)
        btn.setCheckable(True)
        btn.setMaximumHeight(26)
        btn.setStyleSheet(self._button_style(False))
        btn.toggled.connect(lambda checked, n=name: self._on_toggle(n, checked))
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(lambda pos, n=name: self._on_remove_preset(n))
        self._buttons[name] = btn
        self._btn_layout.addWidget(btn)

    def _remove_button(self, name):
        btn = self._buttons.pop(name, None)
        if btn:
            self._selected_tags.discard(name)
            self._btn_layout.removeWidget(btn)
            btn.deleteLater()

    def _button_style(self, checked):
        if checked:
            return (
                'QPushButton { font-size: 12px; padding: 2px 10px; border: 1px solid #1976D2; '
                'border-radius: 12px; background-color: #1976D2; color: #ffffff; }'
                'QPushButton:hover { background-color: #1565C0; }'
            )
        else:
            return (
                'QPushButton { font-size: 12px; padding: 2px 10px; border: 1px solid #bbb; '
                'border-radius: 12px; background-color: transparent; color: #555; }'
                'QPushButton:hover { border-color: #1976D2; color: #1976D2; }'
            )

    def _on_toggle(self, name, checked):
        if checked:
            self._selected_tags.add(name)
        else:
            self._selected_tags.discard(name)
        btn = self._buttons.get(name)
        if btn:
            btn.setStyleSheet(self._button_style(checked))
        self.selection_changed.emit()

    def _on_add_preset(self):
        if len(self._buttons) >= MAX_PRESET_TAGS:
            QMessageBox.information(
                self.window(), '数量上限',
                f'预设标签最多{MAX_PRESET_TAGS}个，请先右键删除已有的再添加。'
            )
            return
        name, ok = QInputDialog.getText(
            self.window(), '添加预设标签', '标签名称（最多5字）：'
        )
        if ok and name:
            name = name.strip()[:5]
            if not name:
                return
            if name in self._buttons:
                QMessageBox.information(self.window(), '提示', '该标签已存在')
                return
            self._add_button(name)
            self._save_presets()

    def _on_remove_preset(self, name):
        self._remove_button(name)
        self._save_presets()
        self.selection_changed.emit()

    def get_selected_tags(self):
        """返回当前选中的标签名称列表"""
        return list(self._selected_tags)

    def set_selected_tags(self, names):
        """根据给定的标签名列表设置选中状态"""
        for name, btn in self._buttons.items():
            should_check = name in names
            btn.blockSignals(True)
            btn.setChecked(should_check)
            btn.setStyleSheet(self._button_style(should_check))
            btn.blockSignals(False)
        self._selected_tags = set(names)

    def clear_selection(self):
        for name, btn in self._buttons.items():
            btn.blockSignals(True)
            btn.setChecked(False)
            btn.setStyleSheet(self._button_style(False))
            btn.blockSignals(False)
        self._selected_tags.clear()