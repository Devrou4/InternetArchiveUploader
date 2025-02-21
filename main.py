import os
import sys
from os import path
from requests import exceptions
from wakepy import keep, ModeExit

from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw
from PySide6 import QtGui as qtg

from UI.main_window import Ui_MainWindow
from LoginDialog.login_dialog import LoginDialog
from AdditionalMetadataDialog.add_metadata_dialog import AdditionalMetadataDialog

import internetarchive as ia
from internetarchive import exceptions as ia_exception
from re import fullmatch


class OutputRedirector:
    def __init__(self, text_edit, signal):
        self.text_edit = text_edit
        self.signal = signal

    def write(self, text):
        if text.strip():
            text = text.rstrip('\n')
            self.signal.emit(text)

    def flush(self):
        pass


class Uploader(qtc.QObject):
    disable_button = qtc.Signal(bool)
    status = qtc.Signal(str)
    printer = qtc.Signal(str)
    disable_fields = qtc.Signal(bool)
    clear_fields = qtc.Signal()
    relog = qtc.Signal()

    start_upload_signal = qtc.Signal(str, dict, list, ia.ArchiveSession)

    def __init__(self):
        super().__init__()
        self.start_upload_signal.connect(self.upload)

    @qtc.Slot(str, dict, list, ia.ArchiveSession)
    def upload(self, identifier, metadata, filepaths, session):
        self.disable_button.emit(True)
        self.disable_fields.emit(True)

        with keep.running() as m:
            try:
                if not self.item_exists(identifier):

                    self.status.emit("Uploading..")
                    upload = ia.upload(identifier, files=filepaths, metadata=metadata, verbose=True, access_key=session.access_key, secret_key=session.secret_key)

                    if upload[0].status_code == 200:
                        self.printer.emit("\nUpload successful!")
                        self.printer.emit(f"You can visit the item at <a href='https://archive.org/details/{identifier}'>https://archive.org/details/{identifier}</a>")
                        self.status.emit("DONE!")
                        self.clear_fields.emit()
                    else:
                        self.printer.emit(f"Upload failed with status code: {upload[0].status_code}")
                        self.printer.emit("Error details:", upload[0].text)
            except ia_exception.AuthenticationError:
                self.printer.emit("Authentication error")
                self.relog.emit()

            except exceptions.RequestException as e:
                self.printer.emit(f"An error occurred: {e}")
            finally:
                self.disable_button.emit(False)
                self.disable_fields.emit(False)

                if not m.active:
                    raise ModeExit

    def item_exists(self, identifier):
        item = ia.get_item(identifier)
        if item.exists:
            self.printer.emit(f"The identifier '{identifier}' already exists on Internet Archive.")
            return True
        return False


class MainWindow(qtw.QMainWindow, Ui_MainWindow):
    log_signal = qtc.Signal(str)

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.session = ia.get_session(config_file="./ia.ini")

        current_path = path.dirname(__file__)
        assets_folder = path.join(current_path, './assets')
        pixmap = qtg.QPixmap(path.join(assets_folder, 'Internet_Acrhive_Logo.png'))
        pixmap = pixmap.scaled(80, 80, qtc.Qt.AspectRatioMode.KeepAspectRatio, qtc.Qt.TransformationMode.SmoothTransformation)

        self.lb_logo.setPixmap(pixmap)
        self.lb_logo.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)

        self.tb_file.clicked.connect(self.pick_file)
        self.pb_upload.clicked.connect(self.start_upload)
        self.tb_folder.clicked.connect(self.pick_dir)
        self.tb_remove.clicked.connect(self.remove_file)
        self.tb_add_metadata.clicked.connect(self.open_additional_metadata_dialog)

        self.filepaths = []
        self.additional_metadata = {}

        self.uploader = Uploader()
        self.upload_thread = qtc.QThread()
        self.uploader.moveToThread(self.upload_thread)

        self.uploader.disable_button.connect(self.upload_button)
        self.uploader.status.connect(self.update_status)
        self.uploader.printer.connect(self.console_log)
        self.uploader.disable_fields.connect(self.disable_fields)
        self.uploader.clear_fields.connect(self.clear_fields)
        self.uploader.relog.connect(self.relog)

        self.upload_thread.start()

        self.upload_thread.finished.connect(self.upload_thread.quit)
        self.upload_thread.finished.connect(self.upload_thread.wait)
        self.log_signal.connect(self.update_console)

        if not path.isfile("./ia.ini"):
            self.dialog = LoginDialog()
            self.dialog.show()
            self.dialog.logged.connect(self.show)
        else:
            self.show()

        sys.stdout = OutputRedirector(self.tb_console, self.log_signal)
        sys.stderr = OutputRedirector(self.tb_console, self.log_signal)

    def pick_file(self):
        filepath, _ = qtw.QFileDialog.getOpenFileUrl(self, "Select files to upload:")
        if filepath.isValid():
            self.lw_paths.addItem(filepath.toLocalFile())
            self.filepaths.append(filepath.toLocalFile())

    def pick_dir(self):
        dir_path = qtw.QFileDialog.getExistingDirectory(self, "Select directory to upload")
        if path.isdir(dir_path):
            self.lw_paths.addItem(dir_path)
            self.filepaths.append(dir_path)

    def remove_file(self):
        item = self.lw_paths.currentItem()

        if item:
            row = self.lw_paths.row(item)
            self.lw_paths.takeItem(row)
            self.filepaths.remove(item.text().strip())

    def start_upload(self):

        identifier = self.le_identifier.text().strip()

        metadata = {
            'title': self.le_title.text().strip(),
            'description': self.te_description.toPlainText(),
            'creator': self.le_creator.text().strip(),
            'subject': self.le_subject.text().strip().split(','),
            'collection': self.cb_collection.currentText(),
            'mediatype': self.cb_mediatype.currentText()
        }

        metadata.update(self.additional_metadata)

        if self.filepaths and self.validate_identifier(identifier):
            print("Starting upload...")

            self.uploader.start_upload_signal.emit(identifier, metadata, self.filepaths, self.session)

    def validate_identifier(self, identifier):

        if not (5 <= len(identifier) <= 80):
            self.console_log(f"Identifier length must be between 5 and 80 characters (got {len(identifier)}).")
            return False

        if not fullmatch(r'[a-z0-9\-_]+', identifier):
            self.console_log("Invalid identifier. Use only lowercase letters, numbers, dashes (-), and underscores (_).")
            return False

        return True

    def open_additional_metadata_dialog(self):
        self.dialog = AdditionalMetadataDialog()
        self.dialog.show()
        self.dialog.send_metadata.connect(self.fetch_additional_metadata)

    @qtc.Slot()
    def relog(self):
        msgbox = qtw.QMessageBox()
        msgbox.setWindowTitle("Authentication error")
        msgbox.setWindowIcon(qtg.QIcon(qtg.QPixmap(os.path.join("assets", "Internet_Archive_Icon.jpg"))))
        msgbox.setText("Authentication error")
        msgbox.setInformativeText("Do you want to re-log?")
        msgbox.setStandardButtons(qtw.QMessageBox.Ok | qtw.QMessageBox.Cancel)
        ret = msgbox.exec()
        if ret == qtw.QMessageBox.Ok:
            if os.path.isfile("./ia.ini"):
                os.remove("./ia.ini")
                self.close()
                self.dialog = LoginDialog()
                self.dialog.show()

                self.dialog.logged.connect(self.show)

    @qtc.Slot(dict)
    def fetch_additional_metadata(self, metadata):
        self.additional_metadata = metadata

    @qtc.Slot(str)
    def update_status(self, text):
        self.statusBar().showMessage(text)

    @qtc.Slot(bool)
    def upload_button(self, disabled):
        self.pb_upload.setDisabled(disabled)

    @qtc.Slot(bool)
    def disable_fields(self, status):
        self.le_title.setDisabled(status)
        self.le_identifier.setDisabled(status)
        self.le_subject.setDisabled(status)
        self.le_creator.setDisabled(status)
        self.te_description.setDisabled(status)
        self.cb_mediatype.setDisabled(status)
        self.cb_collection.setDisabled(status)
        self.tb_file.setDisabled(status)
        self.tb_folder.setDisabled(status)
        self.tb_remove.setDisabled(status)
        self.tb_add_metadata.setDisabled(status)

    @qtc.Slot()
    def clear_fields(self):
        self.le_title.clear()
        self.le_identifier.clear()
        self.le_subject.clear()
        self.le_creator.clear()
        self.te_description.clear()
        self.cb_mediatype.setCurrentIndex(0)
        self.cb_collection.setCurrentIndex(0)
        self.lw_paths.clear()
        self.filepaths = []

    @qtc.Slot(str)
    def console_log(self, text):
        print(text)

    @qtc.Slot(str)
    def update_console(self, text):
        self.tb_console.append(text)

    def closeEvent(self, event):
        self.upload_thread.quit()
        self.upload_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)

    window = MainWindow()

    sys.exit(app.exec())
