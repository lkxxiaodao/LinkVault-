from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from core.habit_analyzer import HabitAnalyzer


class HabitCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.suggestions = []
        self._setup_ui()

    def _setup_ui(self):
        self.card = QFrame()
        self.card.setFrameStyle(QFrame.StyledPanel)
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        card_layout.addWidget(self.message_label, 1)

        self.action_layout = QHBoxLayout()
        self.action_layout.setSpacing(4)
        card_layout.addLayout(self.action_layout)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 0, 4, 4)
        main_layout.addWidget(self.card)
        self.card.hide()

    def show_suggestions(self, suggestions):
        self.suggestions = suggestions
        if not suggestions:
            self.card.hide()
            return

        self.card.show()
        s = suggestions[0]
        msg = f'我注意到你常在【{s.suggestion_time}】左右打开【{s.bookmark["title"]}】，要为你创建一个定时打开任务吗？'
        self.message_label.setText(msg)

        while self.action_layout.count():
            child = self.action_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        btn_create = QPushButton('创建')
        btn_create.clicked.connect(self._on_create)
        self.action_layout.addWidget(btn_create)

        btn_dismiss = QPushButton('忽略')
        btn_dismiss.clicked.connect(self._on_dismiss)
        self.action_layout.addWidget(btn_dismiss)

    def _on_create(self):
        if not self.suggestions:
            return
        s = self.suggestions[0]
        from core.schedule_engine import ScheduleEngine
        hour, minute = s.suggestion_time.split(':')
        ScheduleEngine.add_schedule(
            name=f'自动 - {s.bookmark["title"]}',
            hour=int(hour),
            minute=int(minute),
            repeat_type='daily',
            bookmark_ids=[s.bookmark['id']]
        )
        self.suggestions.pop(0)
        self.show_suggestions(self.suggestions)

    def _on_dismiss(self):
        if self.suggestions:
            self.suggestions.pop(0)
        self.show_suggestions(self.suggestions)