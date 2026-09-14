from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox, QLineEdit, QPushButton, QHBoxLayout
)

from ..instance import Instance


class SettingsDialog(QDialog):
    def __init__(self, instance: Instance, parent=None):
        super().__init__(parent)
        self.instance = instance
        self.setWindowTitle(f"Settings — {instance.name}")
        self.resize(420, 300)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.min_ram = QSpinBox(); self.min_ram.setRange(256, 32768); self.min_ram.setSingleStep(256)
        self.min_ram.setValue(instance.settings.min_ram_mb)
        form.addRow("Min RAM (MB)", self.min_ram)

        self.max_ram = QSpinBox(); self.max_ram.setRange(512, 65536); self.max_ram.setSingleStep(256)
        self.max_ram.setValue(instance.settings.max_ram_mb)
        form.addRow("Max RAM (MB)", self.max_ram)

        self.java_path = QLineEdit(instance.settings.java_path)
        form.addRow("Java path", self.java_path)

        self.jvm_args = QLineEdit(instance.settings.jvm_args)
        form.addRow("Extra JVM args", self.jvm_args)

        self.width = QSpinBox(); self.width.setRange(320, 7680); self.width.setValue(instance.settings.window_width)
        form.addRow("Window width", self.width)

        self.height = QSpinBox(); self.height.setRange(240, 4320); self.height.setValue(instance.settings.window_height)
        form.addRow("Window height", self.height)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        save = QPushButton("Save"); save.setObjectName("Primary"); save.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _save(self):
        s = self.instance.settings
        s.min_ram_mb = self.min_ram.value()
        s.max_ram_mb = self.max_ram.value()
        s.java_path = self.java_path.text().strip() or "java"
        s.jvm_args = self.jvm_args.text().strip()
        s.window_width = self.width.value()
        s.window_height = self.height.value()
        self.instance.save()
        self.accept()
