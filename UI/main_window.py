# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMenuBar, QPushButton, QSizePolicy, QStatusBar,
    QTextBrowser, QTextEdit, QToolButton, QWidget)
import assets_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(640, 661)
        icon = QIcon()
        icon.addFile(u":/logos/Internet_Archive_Icon.jpg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        MainWindow.setWindowIcon(icon)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.pb_upload = QPushButton(self.centralwidget)
        self.pb_upload.setObjectName(u"pb_upload")

        self.gridLayout.addWidget(self.pb_upload, 1, 0, 1, 1)

        self.widget = QWidget(self.centralwidget)
        self.widget.setObjectName(u"widget")
        self.gridLayout_2 = QGridLayout(self.widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.lb_collection = QLabel(self.widget)
        self.lb_collection.setObjectName(u"lb_collection")

        self.gridLayout_2.addWidget(self.lb_collection, 13, 0, 1, 1)

        self.lb_mediatype = QLabel(self.widget)
        self.lb_mediatype.setObjectName(u"lb_mediatype")

        self.gridLayout_2.addWidget(self.lb_mediatype, 12, 0, 1, 1)

        self.cb_collection = QComboBox(self.widget)
        self.cb_collection.addItem("")
        self.cb_collection.addItem("")
        self.cb_collection.addItem("")
        self.cb_collection.addItem("")
        self.cb_collection.addItem("")
        self.cb_collection.addItem("")
        self.cb_collection.setObjectName(u"cb_collection")

        self.gridLayout_2.addWidget(self.cb_collection, 13, 1, 1, 4)

        self.le_creator = QLineEdit(self.widget)
        self.le_creator.setObjectName(u"le_creator")

        self.gridLayout_2.addWidget(self.le_creator, 11, 1, 1, 4)

        self.lb_subject = QLabel(self.widget)
        self.lb_subject.setObjectName(u"lb_subject")

        self.gridLayout_2.addWidget(self.lb_subject, 15, 0, 1, 1)

        self.te_description = QTextEdit(self.widget)
        self.te_description.setObjectName(u"te_description")

        self.gridLayout_2.addWidget(self.te_description, 14, 1, 1, 4)

        self.le_identifier = QLineEdit(self.widget)
        self.le_identifier.setObjectName(u"le_identifier")

        self.gridLayout_2.addWidget(self.le_identifier, 9, 1, 1, 4)

        self.le_subject = QLineEdit(self.widget)
        self.le_subject.setObjectName(u"le_subject")

        self.gridLayout_2.addWidget(self.le_subject, 15, 1, 1, 4)

        self.lb_description = QLabel(self.widget)
        self.lb_description.setObjectName(u"lb_description")

        self.gridLayout_2.addWidget(self.lb_description, 14, 0, 1, 1)

        self.lb_identifier = QLabel(self.widget)
        self.lb_identifier.setObjectName(u"lb_identifier")

        self.gridLayout_2.addWidget(self.lb_identifier, 9, 0, 1, 1)

        self.le_title = QLineEdit(self.widget)
        self.le_title.setObjectName(u"le_title")

        self.gridLayout_2.addWidget(self.le_title, 10, 1, 1, 4)

        self.lb_creator = QLabel(self.widget)
        self.lb_creator.setObjectName(u"lb_creator")

        self.gridLayout_2.addWidget(self.lb_creator, 11, 0, 1, 1)

        self.lb_title = QLabel(self.widget)
        self.lb_title.setObjectName(u"lb_title")

        self.gridLayout_2.addWidget(self.lb_title, 10, 0, 1, 1)

        self.cb_mediatype = QComboBox(self.widget)
        self.cb_mediatype.addItem("")
        self.cb_mediatype.addItem("")
        self.cb_mediatype.addItem("")
        self.cb_mediatype.addItem("")
        self.cb_mediatype.addItem("")
        self.cb_mediatype.addItem("")
        self.cb_mediatype.setObjectName(u"cb_mediatype")

        self.gridLayout_2.addWidget(self.cb_mediatype, 12, 1, 1, 4)

        self.bl_file = QLabel(self.widget)
        self.bl_file.setObjectName(u"bl_file")

        self.gridLayout_2.addWidget(self.bl_file, 1, 0, 1, 1)

        self.lb_logo = QLabel(self.widget)
        self.lb_logo.setObjectName(u"lb_logo")

        self.gridLayout_2.addWidget(self.lb_logo, 0, 1, 1, 1)

        self.tb_file = QToolButton(self.widget)
        self.tb_file.setObjectName(u"tb_file")
        icon1 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen))
        self.tb_file.setIcon(icon1)

        self.gridLayout_2.addWidget(self.tb_file, 1, 3, 1, 2)

        self.tb_folder = QToolButton(self.widget)
        self.tb_folder.setObjectName(u"tb_folder")
        icon2 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.FolderNew))
        self.tb_folder.setIcon(icon2)

        self.gridLayout_2.addWidget(self.tb_folder, 2, 3, 1, 2)

        self.tb_remove = QToolButton(self.widget)
        self.tb_remove.setObjectName(u"tb_remove")
        icon3 = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditDelete))
        self.tb_remove.setIcon(icon3)

        self.gridLayout_2.addWidget(self.tb_remove, 3, 3, 1, 2)

        self.lw_paths = QListWidget(self.widget)
        self.lw_paths.setObjectName(u"lw_paths")

        self.gridLayout_2.addWidget(self.lw_paths, 1, 1, 3, 1)


        self.gridLayout.addWidget(self.widget, 0, 0, 1, 1)

        self.tb_console = QTextBrowser(self.centralwidget)
        self.tb_console.setObjectName(u"tb_console")
        self.tb_console.setOpenExternalLinks(True)

        self.gridLayout.addWidget(self.tb_console, 2, 0, 1, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 640, 22))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
        QWidget.setTabOrder(self.tb_file, self.tb_folder)
        QWidget.setTabOrder(self.tb_folder, self.tb_remove)
        QWidget.setTabOrder(self.tb_remove, self.le_identifier)
        QWidget.setTabOrder(self.le_identifier, self.le_title)
        QWidget.setTabOrder(self.le_title, self.le_creator)
        QWidget.setTabOrder(self.le_creator, self.cb_mediatype)
        QWidget.setTabOrder(self.cb_mediatype, self.cb_collection)
        QWidget.setTabOrder(self.cb_collection, self.te_description)
        QWidget.setTabOrder(self.te_description, self.le_subject)
        QWidget.setTabOrder(self.le_subject, self.pb_upload)
        QWidget.setTabOrder(self.pb_upload, self.tb_console)
        QWidget.setTabOrder(self.tb_console, self.lw_paths)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Internet Archive Uploader", None))
        self.pb_upload.setText(QCoreApplication.translate("MainWindow", u"Upload", None))
        self.lb_collection.setText(QCoreApplication.translate("MainWindow", u"collection:", None))
        self.lb_mediatype.setText(QCoreApplication.translate("MainWindow", u"mediatype:", None))
        self.cb_collection.setItemText(0, QCoreApplication.translate("MainWindow", u"opensource", None))
        self.cb_collection.setItemText(1, QCoreApplication.translate("MainWindow", u"opensource_audio", None))
        self.cb_collection.setItemText(2, QCoreApplication.translate("MainWindow", u"opensource_movies", None))
        self.cb_collection.setItemText(3, QCoreApplication.translate("MainWindow", u"opensource_media", None))
        self.cb_collection.setItemText(4, QCoreApplication.translate("MainWindow", u"opensource_image", None))
        self.cb_collection.setItemText(5, QCoreApplication.translate("MainWindow", u"open_source_software", None))

        self.lb_subject.setText(QCoreApplication.translate("MainWindow", u"subject:", None))
        self.lb_description.setText(QCoreApplication.translate("MainWindow", u"description:", None))
        self.lb_identifier.setText(QCoreApplication.translate("MainWindow", u"identifier: ", None))
        self.lb_creator.setText(QCoreApplication.translate("MainWindow", u"creator: ", None))
        self.lb_title.setText(QCoreApplication.translate("MainWindow", u"title: ", None))
        self.cb_mediatype.setItemText(0, QCoreApplication.translate("MainWindow", u"data", None))
        self.cb_mediatype.setItemText(1, QCoreApplication.translate("MainWindow", u"texts", None))
        self.cb_mediatype.setItemText(2, QCoreApplication.translate("MainWindow", u"audio", None))
        self.cb_mediatype.setItemText(3, QCoreApplication.translate("MainWindow", u"movies", None))
        self.cb_mediatype.setItemText(4, QCoreApplication.translate("MainWindow", u"image", None))
        self.cb_mediatype.setItemText(5, QCoreApplication.translate("MainWindow", u"software", None))

        self.bl_file.setText(QCoreApplication.translate("MainWindow", u"files: ", None))
        self.lb_logo.setText("")
        self.tb_file.setText("")
        self.tb_folder.setText("")
        self.tb_remove.setText("")
    # retranslateUi

