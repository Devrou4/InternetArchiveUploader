from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw
from PySide6 import QtGui as qtg
import sys

from AdditionalMetadataDialog.UI.preset_dialog import Ui_Dialog


class PresetDialog(qtw.QDialog, Ui_Dialog):
    send_preset = qtc.Signal(dict)

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.pb_cancel.clicked.connect(self.close)
        self.pb_load.clicked.connect(self.get_preset)

        self.lw_presets.addItem("Flash")
        self.lw_presets.addItem("MS-DOS")
        self.lw_presets.addItem("Sega Genesis (US)"),
        self.lw_presets.addItem("Mega Drive (EU, JP)")
        self.lw_presets.addItem("NES (nes)")
        self.lw_presets.addItem("NES (nesp)")
        self.lw_presets.addItem("SNES")
        self.lw_presets.addItem("Gameboy")
        self.lw_presets.addItem("Gameboy  Color")
        self.lw_presets.addItem("Gameboy Advance")
        self.lw_presets.addItem("PlayStation")
        self.lw_presets.addItem("Atari 2600")
        self.lw_presets.addItem("Amiga")

        self.presets = {
            "Flash": {"emulator": "ruffle-swf", "emulator_ext": "swf"},
            "MS-DOS": {"emulator": "dosbox", "emulator_ext": "zip", "emulator_start": "(executable name)"},
            "Sega Genesis (US)": {"emulator": "genesis", "emulator_ext": "bin"},
            "Mega Drive (EU, JP)": {"emulator": "megadriv", "emulator_ext": "bin"},
            "NES (nes)": {"emulator": "nes", "emulator_ext": "nes"},
            "NES (nesp)": {"emulator": "nesp", "emulator_ext": "nes"},
            "SNES": {"emulator": "snes", "emulator_ext": "sfc"},
            "Gameboy": {"emulator": "gameboy", "emulator_ext": "gb"},
            "Gameboy Color": {"emulator": "gbcolor", "emulator_ext": "gbc"},
            "Gameboy Advance": {"emulator": "gba", "emulator_ext": "gba"},
            "PlayStation": {"emulator": "psx", "emulator_ext": "chd"},
            "Atari 2600": {"emulator": "a26", "emulator_ext": "bin"},
            "Amiga": {"emulator": "sae-a500p", "emulator_ext": "adf"},
        }

    def get_preset(self):
        preset = self.presets.get(self.lw_presets.currentItem().text().strip())
        if preset:
            self.send_preset.emit(preset)
            self.close()


if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)

    window = PresetDialog()
    window.show()

    sys.exit(app.exec())