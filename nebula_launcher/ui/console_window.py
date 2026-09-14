from PySide6.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Signal


class ConsoleWindow(QDialog):
    append_text = Signal(str)

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 480)

        layout = QVBoxLayout(self)
        self.text = QPlainTextEdit()
        self.text.setObjectName("Console")
        self.text.setReadOnly(True)
        layout.addWidget(self.text)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        btn_row.addWidget(close)
        layout.addLayout(btn_row)

        self.append_text.connect(self._append)

    def _append(self, line: str):
        self.text.appendPlainText(line)
