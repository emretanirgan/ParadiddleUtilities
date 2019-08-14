# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '.\ParadiddleUtilities.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_ParadiddleUtilities(object):
    def setupUi(self, ParadiddleUtilities):
        ParadiddleUtilities.setObjectName("ParadiddleUtilities")
        ParadiddleUtilities.resize(464, 231)
        self.centralwidget = QtWidgets.QWidget(ParadiddleUtilities)
        self.centralwidget.setObjectName("centralwidget")
        self.selectMidiButton = QtWidgets.QPushButton(self.centralwidget)
        self.selectMidiButton.setGeometry(QtCore.QRect(30, 40, 91, 23))
        self.selectMidiButton.setObjectName("selectMidiButton")
        self.midiLabel = QtWidgets.QLabel(self.centralwidget)
        self.midiLabel.setGeometry(QtCore.QRect(30, 20, 101, 16))
        self.midiLabel.setObjectName("midiLabel")
        self.selectDrumSetButton = QtWidgets.QPushButton(self.centralwidget)
        self.selectDrumSetButton.setGeometry(QtCore.QRect(30, 110, 91, 23))
        self.selectDrumSetButton.setObjectName("selectDrumSetButton")
        self.selectedSetLabel = QtWidgets.QLabel(self.centralwidget)
        self.selectedSetLabel.setGeometry(QtCore.QRect(30, 90, 151, 16))
        self.selectedSetLabel.setObjectName("selectedSetLabel")
        self.convertButton = QtWidgets.QPushButton(self.centralwidget)
        self.convertButton.setGeometry(QtCore.QRect(180, 160, 91, 23))
        self.convertButton.setObjectName("convertButton")
        ParadiddleUtilities.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(ParadiddleUtilities)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 464, 21))
        self.menubar.setObjectName("menubar")
        ParadiddleUtilities.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(ParadiddleUtilities)
        self.statusbar.setObjectName("statusbar")
        ParadiddleUtilities.setStatusBar(self.statusbar)

        self.retranslateUi(ParadiddleUtilities)
        QtCore.QMetaObject.connectSlotsByName(ParadiddleUtilities)

    def retranslateUi(self, ParadiddleUtilities):
        _translate = QtCore.QCoreApplication.translate
        ParadiddleUtilities.setWindowTitle(_translate("ParadiddleUtilities", "Paradiddle Utilities"))
        self.selectMidiButton.setText(_translate("ParadiddleUtilities", "Select Midi"))
        self.midiLabel.setText(_translate("ParadiddleUtilities", "No Midi File Selected"))
        self.selectDrumSetButton.setText(_translate("ParadiddleUtilities", "Select Drum Set"))
        self.selectedSetLabel.setText(_translate("ParadiddleUtilities", "Selected Drum Set: default.rlrr"))
        self.convertButton.setText(_translate("ParadiddleUtilities", "Convert to .rlrr!"))
