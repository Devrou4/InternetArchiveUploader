# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Add_Metadata_Dialog.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QGridLayout, QHBoxLayout,
    QHeaderView, QPushButton, QSizePolicy, QTableWidget,
    QTableWidgetItem, QWidget)
import assets_rc

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        Dialog.resize(287, 434)
        icon = QIcon()
        icon.addFile(u":/logos/Internet_Archive_Icon.jpg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        Dialog.setWindowIcon(icon)
        self.gridLayout = QGridLayout(Dialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.pb_presets = QPushButton(Dialog)
        self.pb_presets.setObjectName(u"pb_presets")

        self.gridLayout.addWidget(self.pb_presets, 3, 0, 1, 2)

        self.tbl_metadata = QTableWidget(Dialog)
        if (self.tbl_metadata.columnCount() < 2):
            self.tbl_metadata.setColumnCount(2)
        __qtablewidgetitem = QTableWidgetItem()
        self.tbl_metadata.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tbl_metadata.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        self.tbl_metadata.setObjectName(u"tbl_metadata")
        self.tbl_metadata.horizontalHeader().setCascadingSectionResizes(False)

        self.gridLayout.addWidget(self.tbl_metadata, 2, 0, 1, 2)

        self.widget_2 = QWidget(Dialog)
        self.widget_2.setObjectName(u"widget_2")
        self.horizontalLayout_2 = QHBoxLayout(self.widget_2)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 3, 0, 3)
        self.pb_ok = QPushButton(self.widget_2)
        self.pb_ok.setObjectName(u"pb_ok")

        self.horizontalLayout_2.addWidget(self.pb_ok)

        self.pb_cancel = QPushButton(self.widget_2)
        self.pb_cancel.setObjectName(u"pb_cancel")

        self.horizontalLayout_2.addWidget(self.pb_cancel)


        self.gridLayout.addWidget(self.widget_2, 4, 0, 1, 2)

        self.widget = QWidget(Dialog)
        self.widget.setObjectName(u"widget")
        self.horizontalLayout = QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 3, 0, 3)
        self.pb_add = QPushButton(self.widget)
        self.pb_add.setObjectName(u"pb_add")

        self.horizontalLayout.addWidget(self.pb_add)

        self.pb_remove = QPushButton(self.widget)
        self.pb_remove.setObjectName(u"pb_remove")

        self.horizontalLayout.addWidget(self.pb_remove)


        self.gridLayout.addWidget(self.widget, 0, 0, 1, 2)


        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Additional Metadata", None))
        self.pb_presets.setText(QCoreApplication.translate("Dialog", u"Presets", None))
        ___qtablewidgetitem = self.tbl_metadata.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("Dialog", u"key", None));
        ___qtablewidgetitem1 = self.tbl_metadata.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("Dialog", u"value", None));
        self.pb_ok.setText(QCoreApplication.translate("Dialog", u"OK", None))
        self.pb_cancel.setText(QCoreApplication.translate("Dialog", u"Cancel", None))
        self.pb_add.setText(QCoreApplication.translate("Dialog", u"Add entry", None))
        self.pb_remove.setText(QCoreApplication.translate("Dialog", u"Remove entry", None))
    # retranslateUi

