from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal

from .. import mojang_api


class VersionFetchThread(QThread):
    done = Signal(list)
    failed = Signal(str)

    def run(self):
        try:
            versions = mojang_api.fetch_version_list()
            self.done.emit(versions)
        except Exception as e:
            self.failed.emit(str(e))


class AddInstanceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Instance")
        self.resize(460, 560)
        self.selected_version_id: str | None = None
        self._all_versions = []

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Instance name"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("My Instance")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Version"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search versions (e.g. 1.20.1, 1.7.10, 24w...)")
        self.search_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search_edit)

        filt_row = QHBoxLayout()
        self.cb_release = QCheckBox("Release"); self.cb_release.setChecked(True)
        self.cb_snapshot = QCheckBox("Snapshot")
        self.cb_beta = QCheckBox("Beta")
        self.cb_alpha = QCheckBox("Alpha")
        for cb in (self.cb_release, self.cb_snapshot, self.cb_beta, self.cb_alpha):
            cb.stateChanged.connect(self._apply_filter)
            filt_row.addWidget(cb)
        layout.addLayout(filt_row)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)

        self.status_label = QLabel("Loading version list...")
        self.status_label.setObjectName("Dim")
        layout.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.create_btn = QPushButton("Create")
        self.create_btn.setObjectName("Primary")
        self.create_btn.clicked.connect(self._on_create)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.create_btn)
        layout.addLayout(btn_row)

        self._thread = VersionFetchThread()
        self._thread.done.connect(self._on_versions_loaded)
        self._thread.failed.connect(self._on_versions_failed)
        self._thread.start()

    def _on_versions_loaded(self, versions):
        self._all_versions = versions
        self.status_label.setText(f"{len(versions)} versions available")
        self._apply_filter()

    def _on_versions_failed(self, err):
        self.status_label.setText(f"Failed to load versions: {err}")

    def _apply_filter(self):
        self.list_widget.clear()
        query = self.search_edit.text().strip().lower()
        type_map = {
            "release": self.cb_release.isChecked(),
            "snapshot": self.cb_snapshot.isChecked(),
            "old_beta": self.cb_beta.isChecked(),
            "old_alpha": self.cb_alpha.isChecked(),
        }
        for v in self._all_versions:
            if not type_map.get(v.type, True):
                continue
            if query and query not in v.id.lower():
                continue
            item = QListWidgetItem(f"{v.id}   [{v.type}]")
            item.setData(Qt.UserRole, v.id)
            self.list_widget.addItem(item)

    def _on_create(self):
        name = self.name_edit.text().strip()
        item = self.list_widget.currentItem()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please enter an instance name.")
            return
        if not item:
            QMessageBox.warning(self, "No version selected", "Please pick a Minecraft version.")
            return
        self.selected_version_id = item.data(Qt.UserRole)
        self.instance_name = name
        self.accept()
