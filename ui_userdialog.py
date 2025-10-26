# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'userdialog.ui'
##
## Created by: Qt User Interface Compiler version 6.9.3
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QGroupBox, QPlainTextEdit,
    QSizePolicy, QTabWidget, QToolButton, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(385, 432)
        self.buttonBox_OK = QDialogButtonBox(Dialog)
        self.buttonBox_OK.setObjectName(u"buttonBox_OK")
        self.buttonBox_OK.setEnabled(False)
        self.buttonBox_OK.setGeometry(QRect(30, 370, 341, 32))
        self.buttonBox_OK.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox_OK.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        self.toolButton_LoadFile = QToolButton(Dialog)
        self.toolButton_LoadFile.setObjectName(u"toolButton_LoadFile")
        self.toolButton_LoadFile.setGeometry(QRect(310, 20, 61, 61))
        self.toolButton_LoadFile.setToolTipDuration(0)
        icon = QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen))
        self.toolButton_LoadFile.setIcon(icon)
        self.toolButton_LoadFile.setIconSize(QSize(30, 30))
        self.tabWidget = QTabWidget(Dialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setEnabled(False)
        self.tabWidget.setGeometry(QRect(20, 90, 351, 251))
        self.tab_3d = QWidget()
        self.tab_3d.setObjectName(u"tab_3d")
        self.plainTextEdit_2 = QPlainTextEdit(self.tab_3d)
        self.plainTextEdit_2.setObjectName(u"plainTextEdit_2")
        self.plainTextEdit_2.setGeometry(QRect(20, 20, 241, 111))
        self.tabWidget.addTab(self.tab_3d, "")
        self.tab_4d = QWidget()
        self.tab_4d.setObjectName(u"tab_4d")
        self.groupBox = QGroupBox(self.tab_4d)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setGeometry(QRect(210, 0, 91, 71))
        self.comboBox_view = QComboBox(self.groupBox)
        self.comboBox_view.addItem("")
        self.comboBox_view.addItem("")
        self.comboBox_view.addItem("")
        self.comboBox_view.setObjectName(u"comboBox_view")
        self.comboBox_view.setGeometry(QRect(10, 30, 69, 22))
        self.plainTextEdit_3 = QPlainTextEdit(self.tab_4d)
        self.plainTextEdit_3.setObjectName(u"plainTextEdit_3")
        self.plainTextEdit_3.setGeometry(QRect(40, 20, 151, 31))
        self.infotext_4D = QPlainTextEdit(self.tab_4d)
        self.infotext_4D.setObjectName(u"infotext_4D")
        self.infotext_4D.setEnabled(False)
        self.infotext_4D.setGeometry(QRect(30, 80, 281, 91))
        self.checkBox_4Dto3D = QCheckBox(self.tab_4d)
        self.checkBox_4Dto3D.setObjectName(u"checkBox_4Dto3D")
        self.checkBox_4Dto3D.setGeometry(QRect(20, 180, 301, 31))
        self.checkBox_4Dto3D.setMaximumSize(QSize(500, 16777215))
        self.checkBox_4Dto3D.setAcceptDrops(False)
        self.checkBox_4Dto3D.setAutoExclusive(False)
        self.checkBox_4Dto3D.setTristate(False)
        self.tabWidget.addTab(self.tab_4d, "")
        self.plainTextEdit_file = QPlainTextEdit(Dialog)
        self.plainTextEdit_file.setObjectName(u"plainTextEdit_file")
        self.plainTextEdit_file.setGeometry(QRect(20, 20, 281, 61))
        self.plainTextEdit_4 = QPlainTextEdit(Dialog)
        self.plainTextEdit_4.setObjectName(u"plainTextEdit_4")
        self.plainTextEdit_4.setGeometry(QRect(20, 370, 181, 31))

        self.retranslateUi(Dialog)
        self.buttonBox_OK.accepted.connect(Dialog.accept)
        self.buttonBox_OK.rejected.connect(Dialog.reject)

        self.tabWidget.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
#if QT_CONFIG(tooltip)
        self.toolButton_LoadFile.setToolTip(QCoreApplication.translate("Dialog", u"Load File", None))
#endif // QT_CONFIG(tooltip)
        self.toolButton_LoadFile.setText(QCoreApplication.translate("Dialog", u"...", None))
        self.plainTextEdit_2.setPlainText(QCoreApplication.translate("Dialog", u"3D File selected: 3D Segtmentation and Re-slicing.\n"
"\n"
"Please select the right Tab once the data is loaded!", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3d), QCoreApplication.translate("Dialog", u"3D", None))
        self.groupBox.setTitle(QCoreApplication.translate("Dialog", u"View", None))
        self.comboBox_view.setItemText(0, "")
        self.comboBox_view.setItemText(1, QCoreApplication.translate("Dialog", u"Coronal", None))
        self.comboBox_view.setItemText(2, QCoreApplication.translate("Dialog", u"Sagittal", None))

        self.plainTextEdit_3.setPlainText(QCoreApplication.translate("Dialog", u"Please select your view", None))
        self.infotext_4D.setPlainText(QCoreApplication.translate("Dialog", u"4D file loaded\n"
"\n"
"After clicking OK below, please click \"Start with MRI tags\" to enter your anatomic regions and MRID islands.", None))
        self.checkBox_4Dto3D.setText(QCoreApplication.translate("Dialog", u"I want to open the 4D volume as 3D volume", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4d), QCoreApplication.translate("Dialog", u"4D", None))
        self.plainTextEdit_file.setPlainText(QCoreApplication.translate("Dialog", u"Please open the MAIN IMAGE.", None))
        self.plainTextEdit_4.setPlainText(QCoreApplication.translate("Dialog", u"Click OK if everything is okay", None))
    # retranslateUi

