# V1.1
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets, QtSerialPort
from PyQt5.QtSerialPort import *  
from PyQt5.QtGui import *  
from PyQt5.QtWidgets import *  
from PyQt5.QtCore import *


class QGradProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.target = -1
        self.valuef = 0.0
        # self.setValue(0)

    def setValueF(self, value: float):
        if self.minimum() <=value <= self.maximum():
            self.valuef = value
        self.repaint()

    def valueF(self):
        return self.valuef

    def set_target(self, target):
        self.target = target
        self.repaint()

    def paintEvent(self, a0: QtGui.QPaintEvent):
        # super().paintEvent(a0)
        n_degrees = self.maximum()-self.minimum()
        w_per_degree = int(self.width()/n_degrees)

        p = QPainter(self)
        

        # drawing the progressbar area
        p.setBrush(QColor("#FFFFFF"))
        p.drawRect(QRect(0,32,self.width(),self.height()-30))

        
        

        # Drawing the current line
        pen2 = QPen(Qt.NoPen)
        p.setPen(pen2)
        p.setBrush(QColor("red"))
        rect = QRectF(self.valueF()*w_per_degree,32,2,self.height()-32)
        p.drawRect(rect)


        pen1 = QPen(QColor("#000000"))
        p.setPen(pen1)
        

        # drawing the graduation lines every degree (and longer line every 5 degrees)
        for deg in range(n_degrees+1):
            h = (self.height()-32)//2 if deg%5 == 0 else (self.height()-32)//4
            rect = QRect(deg*w_per_degree,32,1,h)
            p.drawRect(rect)
        
        # drawing the current and target markers
        t = self.target
        t_polygon = [QPoint(t*w_per_degree,32), QPoint(t*w_per_degree-5,32-5), QPoint(t*w_per_degree-5,32-5-5),
                     QPoint(t*w_per_degree-5+10,32-5-5), QPoint(t*w_per_degree-5+10,32-5-5+5), QPoint(t*w_per_degree,32)
                     ]
        t_marker = QPolygon(t_polygon)
        p.setBrush(QColor("blue"))
        p.drawPolygon(t_marker)
        p.drawText(QPoint(t*w_per_degree-6, 16),str(t))
        p.end()


