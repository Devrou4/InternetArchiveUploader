from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw

from LoginDialog.UI.login_dialog import Ui_Dialog
from uploader.config import ConfigError, ConfigManager
from uploader.proxy import ProxyError, normalize_proxy, redact_proxy
from uploader.settings import AppSettings
from uploader.resources import resource_path


class ConfigureWorker(qtc.QObject):
    succeeded = qtc.Signal()
    failed = qtc.Signal(str)

    def __init__(self, manager: ConfigManager, username: str, password: str):
        super().__init__()
        self._manager = manager
        self._username = username
        self._password = password

    @qtc.Slot()
    def run(self):
        try:
            self._manager.configure(self._username, self._password)
        except ConfigError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # defensive: never surface raw payload
            self.failed.emit(f"Authentication failed ({type(exc).__name__})")
        else:
            self.succeeded.emit()


class LoginDialog(qtw.QDialog, Ui_Dialog):
    logged = qtc.Signal()

    def __init__(self, manager: ConfigManager, settings: AppSettings | None = None):
        super().__init__()
        self.setupUi(self)
        self._manager = manager
        self._settings = settings or AppSettings()
        self._thread: qtc.QThread | None = None
        self._worker: ConfigureWorker | None = None
        self._threaded = True
        self.pb_login.clicked.connect(self.submit)

        # The proxy must be settable BEFORE authenticating: users behind a
        # firewall cannot reach archive.org to log in otherwise.
        remembered = manager.proxy or self._settings.load_proxy() or ""
        self.le_proxy = qtw.QLineEdit(remembered)
        self.le_proxy.setPlaceholderText("http://192.168.195.18:20171 (leave empty for direct)")
        self.le_proxy.setToolTip(
            "Used for login, item lookup and uploads. Leave empty for a direct connection."
        )
        proxy_label = qtw.QLabel("proxy:")
        row = self.gridLayout_2.rowCount()
        self.gridLayout_2.addWidget(proxy_label, row, 0, 1, 1)
        self.gridLayout_2.addWidget(self.le_proxy, row, 1, 1, 1)

        self.lb_status.setText(f"Config: {manager.path}")
        self.lb_status.setWordWrap(True)

        palette = self.palette()
        logo = (
            "Internet_Acrhive_Logo_Black.png"
            if palette.color(qtg.QPalette.Window).value() >= 128
            else "Internet_Acrhive_Logo_White.png"
        )
        pixmap = qtg.QPixmap(str(resource_path(logo)))
        pixmap = pixmap.scaled(
            120,
            120,
            qtc.Qt.AspectRatioMode.KeepAspectRatio,
            qtc.Qt.TransformationMode.SmoothTransformation,
        )
        self.lb_logo.setPixmap(pixmap)
        self.lb_logo.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)

    def submit(self):
        username = self.le_mail.text().strip()
        password = self.le_pass.text()
        if not username or not password:
            self.lb_status.setText("Enter credentials!")
            return

        if not self.apply_proxy():
            return

        self.lb_status.setText(
            f"Config: {self._manager.path}\nProxy: {redact_proxy(self._manager.proxy)}"
        )

        self.pb_login.setDisabled(True)
        self.lb_status.setText("Authenticating…")

        if not self._threaded:
            self._run_inline(username, password)
            return

        self._thread = qtc.QThread(self)
        self._worker = ConfigureWorker(self._manager, username, password)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.succeeded.connect(self._on_success)
        self._worker.failed.connect(self._on_failure)
        self._thread.start()

    def _remember_proxy(self) -> None:
        """Persist the choice so the next launch does not need retyping."""
        try:
            self._settings.save_proxy(self._manager.proxy)
        except OSError:
            pass

    def apply_proxy(self) -> bool:
        """Validate the proxy box and store it on the manager."""
        try:
            proxy = normalize_proxy(self.le_proxy.text())
            self._manager = self._manager.with_proxy(proxy)
        except (ProxyError, ConfigError) as exc:
            self.lb_status.setText(str(exc))
            return False
        return True

    def _run_inline(self, username: str, password: str) -> None:
        """Synchronous path used by tests and headless checks."""
        worker = ConfigureWorker(self._manager, username, password)
        worker.succeeded.connect(self._on_success)
        worker.failed.connect(self._on_failure)
        worker.run()

    @qtc.Slot()
    def _on_success(self):
        self.le_pass.clear()
        self._remember_proxy()
        self._finish_thread()
        self.logged.emit()
        self.close()

    def set_threaded(self, threaded: bool) -> None:
        """Disable the worker thread (tests must not outlive a live QThread)."""
        self._threaded = threaded

    @property
    def manager(self) -> ConfigManager:
        """Carries the proxy chosen here into the main window."""
        return self._manager

    @qtc.Slot(str)
    def _on_failure(self, message: str):
        self.le_pass.clear()
        self.lb_status.setText(message)
        self.pb_login.setDisabled(False)
        self._finish_thread()

    def _finish_thread(self):
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            self._worker = None

    def closeEvent(self, event):
        self._finish_thread()
        event.accept()