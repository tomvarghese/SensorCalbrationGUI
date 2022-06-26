import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets, QtSerialPort
from PyQt5.QtSerialPort import *  
from PyQt5.QtGui import *  
from PyQt5.QtWidgets import *  
from PyQt5.QtCore import *

class QCalibrationView(QGraphicsView):

    # COL_SELECTED = Qt.red 
    # COL_NSELECTED = Qt.gray 
    ARM = 300
    MAX_ANGLE = 30
    TICK_W = 5
    PERIOD = ARM/(MAX_ANGLE)
        
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        
        self.scene_ = QGraphicsScene()
        self.scene_.setSceneRect(-180, -90, 360, 180);
        self.setScene(self.scene_)
        # Draw a rectangle item, setting the dimensions.
        # rect = QGraphicsRectItem(0, 0, 200, 50)
        self.xp = QGraphicsLineItem(0,0, self.ARM,0)
        self.yn = QGraphicsLineItem(0,0, 0,self.ARM)
        self.xn = QGraphicsLineItem(-self.ARM,0, 0,0)
        self.yp = QGraphicsLineItem(0,-self.ARM, 0,0)
        
        setattr(self.xp, 'objectName','xp')
        setattr(self.yn, 'objectName','yn')
        setattr(self.xn, 'objectName','xn')
        setattr(self.yp, 'objectName','yp')
        
        self.axes = [self.xp, self.yp, self.xn, self.yn]
        self.active_index = -1
        
        print(self.xp.objectName)
        
        # Define the brush (fill).
        pen = QPen(Qt.black)
        pen.setWidth(2)
        
        self.xp.setPen(pen)
        self.xn.setPen(pen)
        self.yp.setPen(pen)
        self.yn.setPen(pen)
        
        self.scene().addItem(self.xp)
        self.scene().addItem(self.xn)
        self.scene().addItem(self.yp)
        self.scene().addItem(self.yn)
        
        # drawing rulers and text
        self.texts = []
        self.grads_xp = []
        
        for i in range(0, self.MAX_ANGLE,5):
            
            grad_xp = QGraphicsLineItem( i*self.PERIOD, self.TICK_W,  i*self.PERIOD, -self.TICK_W)
            grad_xn = QGraphicsLineItem(-i*self.PERIOD, self.TICK_W, -i*self.PERIOD, -self.TICK_W)
            grad_yn = QGraphicsLineItem(-self.TICK_W,i*self.PERIOD, self.TICK_W, i*self.PERIOD)
            grad_yp = QGraphicsLineItem(-self.TICK_W,-i*self.PERIOD, self.TICK_W, -i*self.PERIOD)
            
            self.grads_xp.append(grad_xp)
            self.grads_xp.append(grad_xn)
            self.grads_xp.append(grad_yn)
            self.grads_xp.append(grad_yp)
            
            self.scene().addItem(grad_xp)
            self.scene().addItem(grad_xn)
            self.scene().addItem(grad_yn)
            self.scene().addItem(grad_yp)
            
            
            item_xp = QGraphicsTextItem(f'{i}')
            if i == 0:
                item_xp.setPos(i*self.PERIOD, 0)
            else:
                item_xp.setPos(i*self.PERIOD-7, 0)
            self.scene().addItem(item_xp)
            self.texts.append(item_xp)
            
            if i == 0:
                continue
            
            item_xn = QGraphicsTextItem(f'{i}')
            item_xn.setPos(-i*self.PERIOD-7, 0)
            self.scene().addItem(item_xn)
            self.texts.append(item_xn)
            
            item_yn = QGraphicsTextItem(f'{i}')
            item_yn.setPos(0, i*self.PERIOD-14)
            self.scene().addItem(item_yn)
            self.texts.append(item_yn)
            
            item_yp = QGraphicsTextItem(f'{i}')
            item_yp.setPos(0, -i*self.PERIOD-14)
            self.scene().addItem(item_yp)
            self.texts.append(item_yp)
            
        
        self.value_xp = 0
        self.value_xn = 0
        self.value_yp = 0
        self.value_yn = 0
        
        self.progress_xp = QGraphicsRectItem(0, -4, 0,2*4)
        self.progress_xp.setPen(QPen(Qt.NoPen))
        self.progress_xp.setBrush(QColor(Qt.red))
        self.progress_xp.setZValue(-1)
        
        self.progress_xn = QGraphicsRectItem(0, -4, 0,2*4)
        self.progress_xn.setPen(QPen(Qt.NoPen))
        self.progress_xn.setBrush(QColor(Qt.red))
        self.progress_xn.setZValue(-1)
        
        self.progress_yp = QGraphicsRectItem(-4, 0, 2*4, 0)
        self.progress_yp.setPen(QPen(Qt.NoPen))
        self.progress_yp.setBrush(QColor(Qt.red))
        self.progress_yp.setZValue(-1)
        
        self.progress_yn = QGraphicsRectItem(-4, 0, 2*4, 0)
        self.progress_yn.setPen(QPen(Qt.NoPen))
        self.progress_yn.setBrush(QColor(Qt.red))
        self.progress_yn.setZValue(-1)
        
        
        
        self.scene().addItem(self.progress_xp)
        self.scene().addItem(self.progress_xn)
        self.scene().addItem(self.progress_yp)
        self.scene().addItem(self.progress_yn)
        
    def set_value_xp(self, value):
        if 0 > value or value > self.MAX_ANGLE:
            return
        self.value_xp = value
        rect = self.progress_xp.rect()
        rect.setX(0)
        rect.setY(-4)
        rect.setWidth(value*self.PERIOD)
        rect.setHeight(8)
        self.progress_xp.setRect(rect)
        
        self.update()
        self.repaint()
    
    def set_value_yp(self, value):
        if 0 > value or value > self.MAX_ANGLE:
            return
        self.value_yp = value
        rect = self.progress_yp.rect()
        rect.setY(-value*self.PERIOD)
        rect.setX(-4)
        rect.setHeight(value*self.PERIOD)
        rect.setWidth(8)
        self.progress_yp.setRect(rect)
        
        self.update()
        self.repaint()
        
    def set_value_xn(self, value):
        if 0 > value or value > self.MAX_ANGLE:
            return
        self.value_xn = value
        rect = self.progress_xn.rect()
        rect.setX(-value*self.PERIOD)
        rect.setY(-4)
        rect.setWidth(value*self.PERIOD)
        rect.setHeight(8)
        self.progress_xn.setRect(rect)
        
        self.update()
        self.repaint()
    
    def set_value_yn(self, value):
        if 0 > value or value > self.MAX_ANGLE:
            return
        self.value_yn = value
        rect = self.progress_yn.rect()
        rect.setY(0)
        rect.setX(-4)
        rect.setHeight(value*self.PERIOD)
        rect.setWidth(8)
        self.progress_yn.setRect(rect)
        
        self.update()
        self.repaint()
              
