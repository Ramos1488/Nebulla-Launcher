from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QMessageBox, QInputDialog, QComboBox
)
from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QIcon

from .. import config
from ..instance import InstanceManager, Instance, ensure_version_ready
from ..auth import load_accounts, add_account, offline_account, Account, login_microsoft_full, MicrosoftLoginError
from .. import launcher_process
from .add_instance_dialog import AddInstanceDialog
from .settings_dialog import SettingsDialog
from .console_window import ConsoleWindow


class PrepareThread(QThread):
    progress = Signal(int, int, str)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, version_id: str):
        super().__init__()
        self.version_id = version_id

    def run(self):
        try:
            vjson = ensure_version_ready(
                self.version_id,
                progress=lambda done, total, label: self.progress.emit(done, total, label),
            )
            self.finished_ok.emit(vjson)
        except Exception as e:
            self.failed.emit(str(e))


class GameOutputThread(QThread):
    line = Signal(str)
    exited = Signal(int)

    def __init__(self, proc):
        super().__init__()
        self.proc = proc

    def run(self):
        for raw in self.proc.stdout:
            self.line.emit(raw.rstrip())
        code = self.proc.wait()
        self.exited.emit(code)


class MicrosoftLoginThread(QThread):
    code_ready = Signal(str, str)
    done = Signal(object)
    failed = Signal(str)

    def run(self):
        try:
            account = login_microsoft_full(on_code=lambda code, url: self.code_ready.emit(code, url))
            self.done.emit(account)
        except MicrosoftLoginError as e:
            self.failed.emit(str(e))
        except Exception as e:
            self.failed.emit(f"Unexpected error: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.resize(920, 600)

        self.manager = InstanceManager()
        self.accounts: list[Account] = load_accounts()
        self.current_account: Account | None = self.accounts[0] if self.accounts else None

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- sidebar -----------------------------------------------------
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        sb_layout = QVBoxLayout(sidebar)
        title = QLabel(config.APP_NAME)
        title.setObjectName("Title")
        sb_layout.addWidget(title)
        subtitle = QLabel("all-versions launcher")
        subtitle.setObjectName("Dim")
        sb_layout.addWidget(subtitle)
        sb_layout.addSpacing(20)

        sb_layout.addWidget(QLabel("Account"))
        self.account_combo = QComboBox()
        self._refresh_account_combo()
        self.account_combo.currentIndexChanged.connect(self._on_account_changed)
        sb_layout.addWidget(self.account_combo)

        self.add_offline_btn = QPushButton("Add offline account")
        self.add_offline_btn.clicked.connect(self._add_offline_account)
        sb_layout.addWidget(self.add_offline_btn)

        self.add_ms_btn = QPushButton("Sign in with Microsoft")
        self.add_ms_btn.clicked.connect(self._add_microsoft_account)
        sb_layout.addWidget(self.add_ms_btn)

        sb_layout.addStretch()
        root.addWidget(sidebar)

        # --- main panel ----------------------------------------------------
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)

        toolbar = QWidget()
        toolbar.setObjectName("Toolbar")
        tb_layout = QHBoxLayout(toolbar)
        self.new_btn = QPushButton("+ New Instance")
        self.new_btn.setObjectName("Primary")
        self.new_btn.clicked.connect(self._new_instance)
        tb_layout.addWidget(self.new_btn)

        self.launch_btn = QPushButton("Launch")
        self.launch_btn.setObjectName("Primary")
        self.launch_btn.clicked.connect(self._launch_selected)
        tb_layout.addWidget(self.launch_btn)

        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self._open_settings)
        tb_layout.addWidget(self.settings_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_selected)
        tb_layout.addWidget(self.delete_btn)

        tb_layout.addStretch()
        panel_layout.addWidget(toolbar)

        self.instance_list = QListWidget()
        self.instance_list.setViewMode(QListWidget.IconMode)
        self.instance_list.setIconSize(QSize(64, 64))
        self.instance_list.setResizeMode(QListWidget.Adjust)
        self.instance_list.setGridSize(QSize(140, 120))
        self.instance_list.setMovement(QListWidget.Static)
        panel_layout.addWidget(self.instance_list, 1)

        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("Dim")
        panel_layout.addWidget(self.status_label)

        root.addWidget(panel, 1)

        self._reload_instances()

    # ---------------------------------------------------------------- utils
    def _refresh_account_combo(self):
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        for acc in self.accounts:
            label = f"{acc.username} ({'MS' if acc.kind == 'microsoft' else 'offline'})"
            self.account_combo.addItem(label)
        if self.accounts:
            idx = self.accounts.index(self.current_account) if self.current_account in self.accounts else 0
            self.account_combo.setCurrentIndex(idx)
        self.account_combo.blockSignals(False)

    def _on_account_changed(self, idx: int):
        if 0 <= idx < len(self.accounts):
            self.current_account = self.accounts[idx]

    def _reload_instances(self):
        self.instance_list.clear()
        icon = QIcon.fromTheme("applications-games")
        for inst in self.manager.list_instances():
            item = QListWidgetItem(inst.name)
            item.setData(Qt.UserRole, inst)
            item.setToolTip(inst.version_id)
            if not icon.isNull():
                item.setIcon(icon)
            self.instance_list.addItem(item)

    def _selected_instance(self) -> Instance | None:
        item = self.instance_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    # ------------------------------------------------------------ accounts
    def _add_offline_account(self):
        name, ok = QInputDialog.getText(self, "Offline account", "Username:")
        if ok and name.strip():
            acc = offline_account(name.strip())
            add_account(acc)
            self.accounts = load_accounts()
            self.current_account = acc
            self._refresh_account_combo()

    def _add_microsoft_account(self):
        self._ms_thread = MicrosoftLoginThread()
        self._ms_thread.code_ready.connect(self._on_ms_code)
        self._ms_thread.done.connect(self._on_ms_done)
        self._ms_thread.failed.connect(self._on_ms_failed)
        self.status_label.setText("Starting Microsoft sign-in...")
        self._ms_thread.start()

    def _on_ms_code(self, code: str, url: str):
        QMessageBox.information(
            self, "Microsoft sign-in",
            f"Open {url} in a browser and enter this code:\n\n{code}\n\n"
            "Click OK once you've signed in and this dialog will keep waiting in the background."
        )
        self.status_label.setText("Waiting for Microsoft sign-in to complete...")

    def _on_ms_done(self, account: Account):
        self.accounts = load_accounts()
        self.current_account = account
        self._refresh_account_combo()
        self.status_label.setText(f"Signed in as {account.username}.")

    def _on_ms_failed(self, err: str):
        self.status_label.setText("Microsoft sign-in failed.")
        QMessageBox.warning(self, "Microsoft sign-in failed", err)

    # ------------------------------------------------------------ instances
    def _new_instance(self):
        dlg = AddInstanceDialog(self)
        if dlg.exec():
            self.manager.create_instance(dlg.instance_name, dlg.selected_version_id)
            self._reload_instances()

    def _open_settings(self):
        inst = self._selected_instance()
        if not inst:
            QMessageBox.information(self, "No instance", "Select an instance first.")
            return
        SettingsDialog(inst, self).exec()

    def _delete_selected(self):
        inst = self._selected_instance()
        if not inst:
            return
        reply = QMessageBox.question(self, "Delete instance", f"Delete '{inst.name}'? This removes all its data.")
        if reply == QMessageBox.Yes:
            self.manager.delete_instance(inst)
            self._reload_instances()

    def _launch_selected(self):
        inst = self._selected_instance()
        if not inst:
            QMessageBox.information(self, "No instance", "Select an instance first.")
            return
        if not self.current_account:
            QMessageBox.information(self, "No account", "Add an offline or Microsoft account first.")
            return

        self.status_label.setText(f"Preparing {inst.version_id}...")
        self.launch_btn.setEnabled(False)
        self._prepare_thread = PrepareThread(inst.version_id)
        self._prepare_thread.progress.connect(self._on_prepare_progress)
        self._prepare_thread.finished_ok.connect(lambda vjson: self._on_prepared(inst, vjson))
        self._prepare_thread.failed.connect(self._on_prepare_failed)
        self._prepare_thread.start()

    def _on_prepare_progress(self, done: int, total: int, label: str):
        self.status_label.setText(f"Downloading ({done}/{max(total,1)}): {label}")

    def _on_prepare_failed(self, err: str):
        self.launch_btn.setEnabled(True)
        self.status_label.setText("Preparation failed.")
        QMessageBox.critical(self, "Failed to prepare version", err)

    def _on_prepared(self, inst: Instance, vjson: dict):
        self.launch_btn.setEnabled(True)
        self.status_label.setText(f"Launching {inst.name}...")
        try:
            proc = launcher_process.launch(inst, vjson, self.current_account)
        except FileNotFoundError:
            QMessageBox.critical(self, "Java not found",
                                  "Could not find/run Java. Set the correct Java path in instance Settings.")
            self.status_label.setText("Launch failed: Java not found.")
            return
        except Exception as e:
            QMessageBox.critical(self, "Launch failed", str(e))
            self.status_label.setText("Launch failed.")
            return

        console = ConsoleWindow(f"{inst.name} — log", self)
        console.show()
        out_thread = GameOutputThread(proc)
        out_thread.line.connect(console.append_text.emit)
        out_thread.exited.connect(lambda code: self.status_label.setText(f"{inst.name} exited (code {code})."))
        out_thread.start()
        # keep references alive
        self._active_console = console
        self._active_out_thread = out_thread
