from pathlib import Path

from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw

from uploader.config_paths import resolve_config_path
from uploader.proxy import ProxyError, normalize_proxy


class SettingsDialog(qtw.QDialog):
    """Non-interactive pieces only: a plain form + signals."""

    config_selected = qtc.Signal(str)
    limit_selected = qtc.Signal(int)
    proxy_selected = qtc.Signal(str)

    def __init__(self, config_path: Path, limit: int, proxy: str | None = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self._config_path = Path(config_path)

        layout = qtw.QFormLayout(self)

        self.config_field = qtw.QLineEdit(str(self._config_path))
        browse = qtw.QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row = qtw.QHBoxLayout()
        row.addWidget(self.config_field)
        row.addWidget(browse)
        layout.addRow("Auth config (ia.ini)", row)

        self.proxy_field = qtw.QLineEdit(proxy or "")
        self.proxy_field.setPlaceholderText("http://192.168.195.18:20171")
        self.proxy_field.setToolTip(
            "Leave empty for a direct connection. Applies to login, queries and uploads."
        )
        layout.addRow("HTTP proxy", self.proxy_field)

        self.limit_field = qtw.QSpinBox()
        self.limit_field.setRange(1, 8)
        self.limit_field.setValue(limit)
        layout.addRow("Concurrent uploads", self.limit_field)

        self.error_label = qtw.QLabel("")
        self.error_label.setStyleSheet("color: rgb(200, 0, 0);")
        self.error_label.setWordWrap(True)
        layout.addRow(self.error_label)

        buttons = qtw.QDialogButtonBox(
            qtw.QDialogButtonBox.StandardButton.Save
            | qtw.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _browse(self):
        chosen, _ = qtw.QFileDialog.getSaveFileName(
            self, "Select ia.ini", str(self._config_path), "INI files (*.ini)"
        )
        if chosen:
            self.config_field.setText(chosen)

    def _save(self):
        path = self.config_field.text().strip()
        if not path:
            self.error_label.setText("Choose a configuration file first.")
            return

        try:
            proxy = normalize_proxy(self.proxy_field.text())
        except ProxyError as exc:
            self.error_label.setText(str(exc))
            return

        self.error_label.setText("")
        resolved = resolve_config_path(path, None)
        self.config_selected.emit(str(resolved))
        self.limit_selected.emit(self.limit_field.value())
        self.proxy_selected.emit(proxy or "")
        self.accept()