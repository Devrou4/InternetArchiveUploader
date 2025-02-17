from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw
from PySide6 import QtGui as qtg
import sys

from AdditionalMetadataDialog.UI.Add_Metadata_Dialog import Ui_Dialog
from AdditionalMetadataDialog.load_preset_dialog import PresetDialog


class AdditionalMetadataDialog(qtw.QDialog, Ui_Dialog):
    send_metadata = qtc.Signal(dict)

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.tbl_metadata.horizontalHeader().setSectionResizeMode(0, qtw.QHeaderView.ResizeMode.Stretch)
        self.tbl_metadata.horizontalHeader().setSectionResizeMode(1, qtw.QHeaderView.ResizeMode.Stretch)
        self.tbl_metadata.verticalHeader().hide()

        self.pb_cancel.clicked.connect(self.close)
        self.pb_ok.clicked.connect(self.get_metadata)

        self.pb_add.clicked.connect(self.add_row)
        self.pb_remove.clicked.connect(self.remove_row)
        self.pb_presets.clicked.connect(self.open_presets_dialog)

    def add_row(self):
        self.tbl_metadata.insertRow(self.tbl_metadata.rowCount())

    def remove_row(self):
        self.tbl_metadata.removeRow(self.tbl_metadata.currentRow())

    def get_metadata(self):
        rows = self.tbl_metadata.rowCount()
        metadata_dic = {}

        for i in range(rows):
            key = self.tbl_metadata.item(i, 0).text().strip()
            value = self.tbl_metadata.item(i, 1).text().strip()

            metadata_dic[key] = value

        self.send_metadata.emit(metadata_dic)
        self.close()

    def open_presets_dialog(self):
        self.dialog = PresetDialog()
        self.dialog.show()
        self.dialog.send_preset.connect(self.load_preset)

    @qtc.Slot(dict)
    def load_preset(self, preset):
        self.tbl_metadata.setRowCount(0)
        if preset:
            for key, value in preset.items():
                index = self.tbl_metadata.rowCount()
                self.add_row()

                if not self.tbl_metadata.item(index, 0):
                    self.tbl_metadata.setItem(index, 0, qtw.QTableWidgetItem())
                if not self.tbl_metadata.item(index, 1):
                    self.tbl_metadata.setItem(index, 1, qtw.QTableWidgetItem())

                self.tbl_metadata.item(index, 0).setText(key)
                self.tbl_metadata.item(index, 1).setText(value)


if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)

    window = AdditionalMetadataDialog()
    window.show()

    sys.exit(app.exec())