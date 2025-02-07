# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'login_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.7.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QSpacerItem,
    QWidget)
import assets_rc

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(340, 239)
        icon = QIcon()
        icon.addFile(u":/logos/Internet_Archive_Icon.jpg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        Dialog.setWindowIcon(icon)
        self.gridLayout = QGridLayout(Dialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.widget = QWidget(Dialog)
        self.widget.setObjectName(u"widget")
        self.gridLayout_2 = QGridLayout(self.widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.lb_pass = QLabel(self.widget)
        self.lb_pass.setObjectName(u"lb_pass")

        self.gridLayout_2.addWidget(self.lb_pass, 4, 0, 1, 2)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer_2, 8, 0, 1, 2)

        self.lb_mail = QLabel(self.widget)
        self.lb_mail.setObjectName(u"lb_mail")

        self.gridLayout_2.addWidget(self.lb_mail, 2, 0, 1, 2)

        self.lb_status = QLabel(self.widget)
        self.lb_status.setObjectName(u"lb_status")
        self.lb_status.setStyleSheet(u"color: rgb(255, 0, 0);")

        self.gridLayout_2.addWidget(self.lb_status, 7, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout_2.addItem(self.verticalSpacer, 1, 0, 1, 2)

        self.le_mail = QLineEdit(self.widget)
        self.le_mail.setObjectName(u"le_mail")

        self.gridLayout_2.addWidget(self.le_mail, 3, 0, 1, 2)

        self.le_pass = QLineEdit(self.widget)
        self.le_pass.setObjectName(u"le_pass")
        self.le_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.le_pass.setClearButtonEnabled(False)

        self.gridLayout_2.addWidget(self.le_pass, 6, 0, 1, 2)

        self.lb_logo = QLabel(self.widget)
        self.lb_logo.setObjectName(u"lb_logo")

        self.gridLayout_2.addWidget(self.lb_logo, 0, 0, 1, 2)


        self.gridLayout.addWidget(self.widget, 0, 0, 1, 2)

        self.pb_login = QPushButton(Dialog)
        self.pb_login.setObjectName(u"pb_login")

        self.gridLayout.addWidget(self.pb_login, 2, 0, 1, 2)


        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Internet Archive Uploader Login", None))
        self.lb_pass.setText(QCoreApplication.translate("Dialog", u"Password:", None))
        self.lb_mail.setText(QCoreApplication.translate("Dialog", u"E-Mail:", None))
        self.lb_status.setText("")
        self.lb_logo.setText("")
        self.pb_login.setText(QCoreApplication.translate("Dialog", u"Login", None))
    # retranslateUi

