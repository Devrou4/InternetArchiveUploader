from pathlib import Path

from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw

from uploader.config_paths import resolve_config_path


class SettingsDialog(qtw.QDialog):
    """Non-interactive pieces only: a plain form + signal."""

    config_selected = qtc.Signal(str)
    limit_selected = qtc.Signal(int)

    def __init__(self, config_path: Path, limit: int, parent=None):
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

        self.limit_field = qtw.QSpinBox()
        self.limit_field.setRange(1, 8)
        self.limit_field.setValue(limit)
        layout.addRow("Concurrent uploads", self.limit_field)

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
            return
        resolved = resolve_config_path(path, None)
        self.config_selected.emit(str(resolved))
        self.limit_selected.emit(self.limit_field.value())
        self.accept()