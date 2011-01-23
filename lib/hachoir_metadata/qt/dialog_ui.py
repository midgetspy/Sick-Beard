# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'hachoir_metadata/qt/dialog.ui'
#
# Created: Mon Jul 26 03:10:06 2010
#      by: PyQt4 UI code generator 4.7.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(441, 412)
        self.verticalLayout = QtGui.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.open_button = QtGui.QPushButton(Form)
        self.open_button.setObjectName("open_button")
        self.horizontalLayout_2.addWidget(self.open_button)
        self.files_combo = QtGui.QComboBox(Form)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.files_combo.sizePolicy().hasHeightForWidth())
        self.files_combo.setSizePolicy(sizePolicy)
        self.files_combo.setObjectName("files_combo")
        self.horizontalLayout_2.addWidget(self.files_combo)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.metadata_table = QtGui.QTableWidget(Form)
        self.metadata_table.setAlternatingRowColors(True)
        self.metadata_table.setShowGrid(False)
        self.metadata_table.setRowCount(0)
        self.metadata_table.setColumnCount(0)
        self.metadata_table.setObjectName("metadata_table")
        self.metadata_table.setColumnCount(0)
        self.metadata_table.setRowCount(0)
        self.verticalLayout.addWidget(self.metadata_table)
        self.quit_button = QtGui.QPushButton(Form)
        self.quit_button.setObjectName("quit_button")
        self.verticalLayout.addWidget(self.quit_button)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "hachoir-metadata", None, QtGui.QApplication.UnicodeUTF8))
        self.open_button.setText(QtGui.QApplication.translate("Form", "Open", None, QtGui.QApplication.UnicodeUTF8))
        self.quit_button.setText(QtGui.QApplication.translate("Form", "Quit", None, QtGui.QApplication.UnicodeUTF8))

