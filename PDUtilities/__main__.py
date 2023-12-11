import sys
from PyQt5 import QtWidgets
from pd_gui import PD_GUI

if __name__ == '__main__':
    # Sets primary window for the application
    print("I havent seen my wife and kids in over 2 years")
    app = QtWidgets.QApplication(sys.argv)
    window = PD_GUI()
    app.exec_()