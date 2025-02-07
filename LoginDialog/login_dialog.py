from PySide6 import QtCore as qtc
from PySide6 import QtWidgets as qtw
from PySide6 import QtGui as qtg
import sys
from os import path
import internetarchive as ia

from LoginDialog.UI.login_dialog import Ui_Dialog


class LoginDialog(qtw.QDialog, Ui_Dialog):
    logged = qtc.Signal()

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.pb_login.clicked.connect(self.submit)

        current_path = path.dirname(__file__)
        assets_folder = path.join(current_path, '../assets')
        pixmap = qtg.QPixmap(path.join(assets_folder, 'Internet_Acrhive_Logo.png'))
        pixmap = pixmap.scaled(120, 120, qtc.Qt.AspectRatioMode.KeepAspectRatio, qtc.Qt.TransformationMode.SmoothTransformation)

        self.lb_logo.setPixmap(pixmap)
        self.lb_logo.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)

    def submit(self):
        mail = self.le_mail.text().strip()
        password = self.le_pass.text().strip()
        if mail and password:
            try:
                self.pb_login.setDisabled(True)
                request = ia.configure(username=mail, password=password, config_file='./ia.ini')
                if request:
                    self.logged.emit()
                    self.close()

            except Exception as e:
                pass
            self.pb_login.setDisabled(False)
            self.lb_status.setText("Incorrect credentials!")
        else:
            self.lb_status.setText("Enter credentials!")


if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)

    window = LoginDialog()
    window.show()

    sys.exit(app.exec())