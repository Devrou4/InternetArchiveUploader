import argparse
import os
import sys
from pathlib import Path
from os import path

from requests import exceptions
from wakepy import keep, ModeExit

from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw
from PySide6 import QtGui as qtg

from UI.main_window import Ui_MainWindow
from LoginDialog.login_dialog import LoginDialog
from AdditionalMetadataDialog.add_metadata_dialog import AdditionalMetadataDialog
from uploader.config import ConfigError, ConfigManager
from uploader.config_paths import resolve_config_path, resolve_proxy
from uploader.controller import UploadController
from uploader.proxy import ProxyError, redact_proxy
from uploader.models import ItemConfig, TaskState
from uploader.queue import TaskQueue
from uploader.resources import resource_path
from uploader.settings import AppSettings
from uploader.widgets.settings_dialog import SettingsDialog
from uploader.widgets.task_table import TaskTable

import internetarchive as ia
from internetarchive import exceptions as ia_exception
from re import fullmatch


class MainWindow(qtw.QMainWindow, Ui_MainWindow):
    log_signal = qtc.Signal(str)

    def __init__(self, manager: ConfigManager):
        super().__init__()
        self.setupUi(self)
        self.manager = manager
        self.additional_metadata = {}
        self.current_config = manager.path

        palette = self.palette()
        window_color = palette.color(qtg.QPalette.Window)
        self.theme = 'dark' if window_color.value() < 128 else 'light'

        logo = 'Internet_Acrhive_Logo_Black.png' if self.theme == 'light' else 'Internet_Acrhive_Logo_White.png'
        pixmap = qtg.QPixmap(str(resource_path(logo)))
        pixmap = pixmap.scaled(
            80, 80,
            qtc.Qt.AspectRatioMode.KeepAspectRatio,
            qtc.Qt.TransformationMode.SmoothTransformation,
        )
        self.lb_logo.setPixmap(pixmap)
        self.lb_logo.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)

        self.queue = TaskQueue(limit=2)
        self.controller = UploadController(manager, self.queue)

        # The import row (Select file / folder / remove) already occupies grid
        # rows 1-3, so the task table lives in its own container placed below
        # the whole form. Overlapping the two is what hid the buttons before.
        self.tasks = TaskTable(config_path=manager.path)
        self.tasks.setMinimumHeight(160)
        self.lw_paths.hide()

        self.limit_box = qtw.QSpinBox()
        self.limit_box.setRange(1, 8)
        self.limit_box.setValue(2)
        self.limit_box.setToolTip("Simultaneous file uploads")

        self.pb_stop = qtw.QPushButton("Stop dispatching")
        self.pb_retry = qtw.QPushButton("Retry failed")
        self.tb_settings = qtw.QToolButton()
        self.tb_settings.setText("Settings")
        self.gridLayout_2.addWidget(self.tb_settings, 0, 4, 1, 1)

        controls = qtw.QHBoxLayout()
        controls.addWidget(qtw.QLabel("Concurrent uploads:"))
        controls.addWidget(self.limit_box)
        controls.addStretch(1)
        controls.addWidget(self.pb_stop)
        controls.addWidget(self.pb_retry)
        self.controls_row = qtw.QWidget()
        self.controls_row.setLayout(controls)
        self.gridLayout_2.addWidget(self.controls_row, 17, 0, 1, 5)

        self.config_label = qtw.QLabel(self._connection_text())
        self.config_label.setWordWrap(True)
        self.gridLayout_2.addWidget(self.config_label, 18, 0, 1, 5)

        self.central_layout = qtw.QVBoxLayout()
        self.centralwidget.layout().removeWidget(self.widget)
        self.central_layout.addWidget(self.widget)
        self.central_layout.addWidget(self.tasks, 1)
        self.centralwidget.layout().addLayout(self.central_layout, 0, 0, 1, 1)

        self._relabel_import_buttons()

        self.tb_file.clicked.connect(self.pick_file)
        self.tb_folder.clicked.connect(self.pick_folder_notice)
        self.tb_remove.clicked.connect(self.remove_selected)
        self.tb_add_metadata.clicked.connect(self.open_additional_metadata_dialog)
        self.pb_upload.clicked.connect(self.start_upload)
        self.pb_stop.clicked.connect(self.stop_dispatch)
        self.pb_retry.clicked.connect(self.retry_failed)
        self.tb_settings.clicked.connect(self.open_settings)
        self.limit_box.valueChanged.connect(self.controller.set_limit)

        self.controller.log.connect(self.update_console)
        self.controller.status.connect(self.update_status)
        self.controller.state_changed.connect(self.refresh_tasks)
        self.controller.item_lookup_failed.connect(self._on_lookup_failed)

        if not manager.path.is_file():
            self.dialog = LoginDialog(manager)
            self.dialog.show()
            self.dialog.logged.connect(self._after_login)
        else:
            self.show()

    # ---- login ---------------------------------------------------------
    @qtc.Slot()
    def _after_login(self):
        if getattr(self, "dialog", None) is not None:
            self._after_login_from(self.dialog)
        else:
            self.controller.reset_session()
            self.show()

    def _after_login_from(self, dialog):
        """Adopt the proxy picked at login so uploads use the same route."""
        if hasattr(dialog, "apply_proxy"):
            dialog.apply_proxy()
        manager = getattr(dialog, "manager", self.manager)
        proxy_changed = manager.proxy != getattr(self.manager, "proxy", None)
        path_changed = Path(manager.path) != Path(self.manager.path)
        if proxy_changed or path_changed:
            self.manager = manager
            self.controller = UploadController(manager, self.queue)
            self._connect_controller()
            self.current_config = manager.path
            self.tasks.set_config_path(manager.path)
            self.config_label.setText(self._connection_text())
        self.controller.reset_session()
        self.show()

    @qtc.Slot()
    def relog(self):
        if self.controller.has_active_tasks():
            qtw.QMessageBox.warning(self, "Uploads running", "Stop dispatching and wait before changing accounts.")
            return
        try:
            os.remove(self.manager.path)
        except OSError:
            pass
        self.controller.reset_session()
        self.dialog = LoginDialog(self.manager)
        self.dialog.show()
        self.dialog.logged.connect(self._after_login)

    def _relabel_import_buttons(self):
        """Icon-only tool buttons render blank when the theme resolves no icon."""
        labels = (
            (self.tb_file, "Select file", "Add files to the upload queue"),
            (self.tb_folder, "Folder", "Folder uploads are not supported yet"),
            (self.tb_remove, "Remove", "Remove the selected rows"),
        )
        for button, text, tip in labels:
            button.setText(text)
            button.setToolTip(tip)
            button.setToolButtonStyle(qtc.Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setMinimumWidth(90)

    # ---- import --------------------------------------------------------
    def pick_file(self):
        paths, _ = qtw.QFileDialog.getOpenFileNames(self, "Select files to upload")
        if paths:
            self.add_paths(paths)

    def pick_folder_notice(self):
        self.update_console("Folder uploads are not supported yet; drop individual files instead.")

    def add_paths(self, paths):
        self.tasks.set_item(self.build_item_config())
        self.tasks.set_config_path(self.current_config)
        added = self.tasks.add_paths(paths)
        if added:
            self.apply_detected_metadata(added)
            self.refresh_tasks()

    def apply_detected_metadata(self, added):
        mediatypes = {getattr(t, "detected_mediatype", None) for t in added}
        mediatypes.discard(None)
        if len(mediatypes) == 1:
            mediatype = mediatypes.pop()
            index = self.cb_mediatype.findText(mediatype)
            if index >= 0:
                self.cb_mediatype.setCurrentIndex(index)
        elif len(mediatypes) > 1:
            self.update_console("Mixed media types detected; choose one media type for this item.")
        if self.le_title.text().strip() == "" and added:
            self.le_title.setText(added[0].local_path.stem)

    def remove_selected(self):
        rows = sorted({index.row() for index in self.tasks.table.selectedIndexes()}, reverse=True)
        self.tasks.remove_rows(rows)

    # ---- item ----------------------------------------------------------
    def build_item_config(self):
        identifier = self.le_identifier.text().strip()
        metadata = {
            'title': self.le_title.text().strip(),
            'description': self.te_description.toPlainText(),
            'creator': self.le_creator.text().strip(),
            'subject': [s.strip() for s in self.le_subject.text().split(',') if s.strip()],
            'collection': self.cb_collection.currentText(),
            'mediatype': self.cb_mediatype.currentText(),
        }
        metadata.update(self.additional_metadata)
        return ItemConfig(identifier=identifier, metadata=metadata)

    def start_upload(self):
        if self.controller.has_active_tasks():
            self.update_console("Uploads already running.")
            return
        item = self.build_item_config()
        if not self.validate_identifier(item.identifier):
            return
        for row, task in enumerate(self.tasks.tasks()):
            if not task.item_key:
                self.tasks.set_item_key_for_rows([row], item.identifier)
        tasks = self.tasks.startable_tasks()
        if not tasks:
            self.update_console("No startable files. Check for name conflicts or missing files.")
            return
        if not self.controller.register_tasks(item, self.tasks.tasks()):
            return
        self.controller.set_limit(self.limit_box.value())
        self.update_console(f"Queued {len(tasks)} file(s) for {item.identifier}.")
        self.controller.start()

    def validate_identifier(self, identifier):
        if not (5 <= len(identifier) <= 80):
            self.update_console(f"Identifier length must be between 5 and 80 characters (got {len(identifier)}).")
            return False
        if any(ch.isspace() for ch in identifier):
            self.update_console("Identifier must not contain spaces.")
            return False
        return True

    def open_additional_metadata_dialog(self):
        self.dialog = AdditionalMetadataDialog()
        self.dialog.show()
        self.dialog.send_metadata.connect(self.fetch_additional_metadata)

    @qtc.Slot(dict)
    def fetch_additional_metadata(self, metadata):
        self.additional_metadata = metadata

    # ---- queue ---------------------------------------------------------
    def stop_dispatch(self):
        self.controller.stop_dispatch()

    def retry_failed(self):
        for task in self.queue.tasks():
            if task.state is TaskState.FAILED:
                self.controller.retry(task.id)
        self.controller.start()

    def refresh_tasks(self):
        self.tasks.refresh()

    @qtc.Slot(str)
    def _on_lookup_failed(self, message):
        self.update_console(f"Item lookup failed: {message}")
        qtw.QMessageBox.warning(self, "Item lookup failed", message)

    # ---- settings ------------------------------------------------------
    def open_settings(self):
        if self.controller.has_active_tasks():
            qtw.QMessageBox.warning(self, "Uploads running", "Stop dispatching and wait before changing settings.")
            return
        dialog = SettingsDialog(
            self.current_config,
            self.limit_box.value(),
            self.manager.proxy or "",
            self,
        )
        dialog.limit_selected.connect(self.limit_box.setValue)
        dialog.config_selected.connect(self.on_config_selected)
        dialog.proxy_selected.connect(self._on_proxy_selected)
        dialog.exec()

    def _connection_text(self) -> str:
        return (
            f"Config: {self.current_config}\n"
            f"Proxy: {redact_proxy(self.manager.proxy)}"
        )

    @qtc.Slot(str)
    def _on_proxy_selected(self, proxy: str):
        if self.controller.has_active_tasks():
            qtw.QMessageBox.warning(self, "Uploads running", "Stop dispatching and wait before changing the proxy.")
            return
        try:
            self.manager = self.manager.with_proxy(proxy)
        except ConfigError as exc:
            qtw.QMessageBox.warning(self, "Invalid proxy", str(exc))
            return
        self.controller = UploadController(self.manager, self.queue)
        self._connect_controller()
        self.current_config = self.manager.path
        self.config_label.setText(self._connection_text())
        self.update_console(
            f"Proxy set to {redact_proxy(self.manager.proxy)}; queued files must be re-checked before starting."
        )

    def _connect_controller(self):
        self.controller.log.connect(self.update_console)
        self.controller.status.connect(self.update_status)
        self.controller.state_changed.connect(self.refresh_tasks)
        self.controller.item_lookup_failed.connect(self._on_lookup_failed)

    def on_config_selected(self, config_path: str):
        new_manager = ConfigManager(Path(config_path))
        if not new_manager.path.is_file():
            qtw.QMessageBox.warning(self, "Not found", f"Configuration file does not exist: {config_path}")
            return
        self.manager = new_manager.with_proxy(self.manager.proxy)
        self.controller = UploadController(self.manager, self.queue)
        self._connect_controller()
        self.current_config = self.manager.path
        self.config_label.setText(self._connection_text())
        self.tasks.set_config_path(new_manager.path)
        self.tasks.set_item(self.build_item_config())
        self.update_console("Configuration changed. Queued files must be re-checked before starting.")

    @qtc.Slot(str)
    def update_status(self, text):
        self.statusBar().showMessage(text)

    @qtc.Slot(str)
    def update_console(self, text):
        self.tb_console.append(text)

    def closeEvent(self, event):
        if self.controller.has_active_tasks():
            choice = qtw.QMessageBox.question(
                self,
                "Uploads running",
                "Stop dispatching and wait for running uploads to finish?",
                qtw.QMessageBox.StandardButton.Yes | qtw.QMessageBox.StandardButton.Cancel,
            )
            if choice != qtw.QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.controller.stop_dispatch()
            if not self.controller.wait_for_active():
                qtw.QMessageBox.warning(self, "Still running", "Uploads are still running; close again later.")
                event.ignore()
                return
        event.accept()


def parse_args(argv: list[str]):
    parser = argparse.ArgumentParser(prog="internetarchive-uploader")
    parser.add_argument("--config", help="Path to the Internet Archive ia.ini file")
    parser.add_argument(
        "--proxy",
        help="HTTP proxy for login, queries and uploads, e.g. http://192.168.195.18:20171",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Build the main window, then exit without authenticating",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = parse_args(argv)

    if sys.platform.startswith('linux'):
        os.environ.setdefault("QT_QPA_PLATFORMTHEME", "xdgdesktopportal")
    app = qtw.QApplication.instance()
    if app is None:
        app = qtw.QApplication(sys.argv)
    app.setApplicationName("iauploader")

    if sys.platform == 'win32':
        app.setStyle("Fusion")

    settings = AppSettings()
    remembered_proxy = settings.load_proxy()
    effective_proxy = resolve_proxy(args.proxy, remembered_proxy)
    try:
        manager = ConfigManager(
            resolve_config_path(args.config, None),
            proxy=effective_proxy,
        )
    except ConfigError as exc:
        print(f"invalid proxy: {exc}", file=sys.stderr)
        return 2

    if args.smoke_test:
        icon = qtg.QPixmap(str(resource_path('Internet_Acrhive_Logo_White.png')))
        if icon.isNull():
            print("smoke-test: logo resource missing", file=sys.stderr)
            return 2
        print("smoke-test: ok")
        return 0

    window = MainWindow(manager)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
