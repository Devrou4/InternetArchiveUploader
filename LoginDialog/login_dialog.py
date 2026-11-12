from PySide6 import QtCore as qtc
from PySide6 import QtGui as qtg
from PySide6 import QtWidgets as qtw

from LoginDialog.UI.login_dialog import Ui_Dialog
from uploader.config import ConfigError, ConfigManager
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

    def __init__(self, manager: ConfigManager):
        super().__init__()
        self.setupUi(self)
        self._manager = manager
        self._thread: qtc.QThread | None = None
        self._worker: ConfigureWorker | None = None
        self.pb_login.clicked.connect(self.submit)
        self.lb_status.setText(f"Config: {manager.path}")

        pixmap = qtg.QPixmap(str(resource_path("Internet_Acrhive_Logo.png")))
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

        self.pb_login.setDisabled(True)
        self.lb_status.setText("Authenticating…")

        self._thread = qtc.QThread(self)
        self._worker = ConfigureWorker(self._manager, username, password)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.succeeded.connect(self._on_success)
        self._worker.failed.connect(self._on_failure)
        self._thread.start()

    @qtc.Slot()
    def _on_success(self):
        self.le_pass.clear()
        self._finish_thread()
        self.logged.emit()
        self.close()

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