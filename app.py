import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import *  
from PyQt5.QtWidgets import *  
from PyQt5.QtCore import *
import sys
from app_core import *
import logging

from qt_material import apply_stylesheet

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app = QApplication(sys.argv)

    mainWin = MainWindow(app)
    mainWin.setWindowTitle('SensorCalibration')
    # mainWin.ui.plot_widget.setBackground(QtGui.QColor('white'))
    # mainWin.ui.plot_widget_xp.setBackground(QtGui.QColor('white'))
    # mainWin.ui.plot_widget_xn.setBackground(QtGui.QColor('white'))
    # mainWin.ui.plot_widget_yp.setBackground(QtGui.QColor('white'))
    # mainWin.ui.plot_widget_yn.setBackground(QtGui.QColor('white'))
    apply_stylesheet(app, theme='light_blue.xml')

    mainWin.show()
    sys.exit(app.exec_())