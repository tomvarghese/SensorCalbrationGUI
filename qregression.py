import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets, QtSerialPort
from PyQt5.QtSerialPort import *  
from PyQt5.QtGui import *  
from PyQt5.QtWidgets import *  
from PyQt5.QtCore import *
import numpy as np
from numpy.core.fromnumeric import argsort
from scipy.ndimage import shift
from sklearn.linear_model import LinearRegression

class QRegression(QObject):
    def __init__(self, parent=None, cal_settings=None):
        super().__init__(parent)
        self.settings = cal_settings

    def linear_fit(self,x,y):

        regr = LinearRegression()
        regr.fit(x.reshape(-1,1), y.reshape(-1,1))
        m, c = regr.coef_, regr.intercept_
        return m,c