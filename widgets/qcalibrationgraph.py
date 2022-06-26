import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets, QtSerialPort
from PyQt5.QtSerialPort import *  
from PyQt5.QtGui import *  
from PyQt5.QtWidgets import *  
from PyQt5.QtCore import *

class QCalibrationGraph(QGraphicsView):
    calibration_finished = pyqtSignal()
    COL_SELECTED = Qt.red 
    COL_NSELECTED = Qt.gray 
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
            
        p_h = [ QPoint(-6, -15), 
                QPoint(6 , -15), 
                QPoint(6 , -3), 
                QPoint(0 , 0),
                QPoint(-6 , -3),  
                QPoint(-6 , -15),  
                QPoint(-6, -15)]

        p_v = [ QPoint(-15,6 ), 
                QPoint(-15,-6 ), 
                QPoint(-3,-6 ),
                QPoint(0 ,0 ),
                QPoint(-3, 6 ), 
                QPoint(-15,6 )]
        
        self.polygon_h = QGraphicsPolygonItem(QPolygonF(p_h))
        self.polygon_h.setPos(0*self.PERIOD, 0)
        self.polygon_h.setPen(QPen(Qt.NoPen))
        self.polygon_h.setBrush(QColor(Qt.blue))
        
        self.polygon_v = QGraphicsPolygonItem(QPolygonF(p_v))
        self.polygon_v.setPos(0, 0*self.PERIOD)
        self.polygon_v.setPen(QPen(Qt.NoPen))
        self.polygon_v.setBrush(QColor(Qt.blue))
        
        self.scene().addItem(self.polygon_h)
        self.scene().addItem(self.polygon_v)
        
        self.polygon_h.hide()
        self.polygon_v.hide()

        self.target = 0
        self.value = 0
        
        self.progress_h = QGraphicsRectItem(0, -4, 0,2*4)
        self.progress_h.setPen(QPen(Qt.NoPen))
        self.progress_h.setBrush(QColor(Qt.red))
        self.progress_h.setZValue(-1)
        
        self.progress_v = QGraphicsRectItem(-4, 0, 2*4, 0)
        self.progress_v.setPen(QPen(Qt.NoPen))
        self.progress_v.setBrush(QColor(Qt.red))
        self.progress_v.setZValue(-1)
        
        
        self.scene().addItem(self.progress_h)
        self.scene().addItem(self.progress_v)
        
    def set_value(self, value):
        if 0 > value or value > self.MAX_ANGLE:
            return
        
        if self.active_index == -1:
            return
        
        axis = self.axes[self.active_index]
        name = axis.objectName
        
        if name == 'xp':
            rect = self.progress_h.rect()
            rect.setX(0)
            rect.setY(-4)
            rect.setWidth(value*self.PERIOD)
            rect.setHeight(8)
            self.progress_h.setRect(rect)

        elif name == 'xn':
            rect = self.progress_h.rect()
            rect.setX(-value*self.PERIOD)
            rect.setY(-4)
            rect.setWidth(value*self.PERIOD)
            rect.setHeight(8)
            self.progress_h.setRect(rect)
            
        elif name == 'yp':
            rect = self.progress_v.rect()
            rect.setY(-value*self.PERIOD)
            rect.setX(-4)
            rect.setHeight(value*self.PERIOD)
            rect.setWidth(8)
            self.progress_v.setRect(rect)
            
        elif name == 'yn':
            rect = self.progress_v.rect()
            rect.setY(0)
            rect.setX(-4)
            rect.setHeight(value*self.PERIOD)
            rect.setWidth(8)
            self.progress_v.setRect(rect)
        
        self.value = value
        self.update()
        self.repaint()
              
    def set_target(self, new_target):
        # get active axis
        if self.active_index == -1:
            return
        
        axis = self.axes[self.active_index]
        name = axis.objectName
        self.set_value(self.value)
        if name == 'xp':
            self.polygon_h.setPos(new_target*self.PERIOD, 0)
            self.polygon_h.show()
            self.polygon_v.hide()
            self.progress_h.show()
            self.progress_v.hide()
            
            
        elif name == 'xn':
            self.polygon_h.setPos(-new_target*self.PERIOD, 0)
            self.polygon_h.show()
            self.polygon_v.hide()
            self.progress_h.show()
            self.progress_v.hide()
            
        
        elif name == 'yp':
            self.polygon_v.setPos(0, -new_target*self.PERIOD)
            self.polygon_v.show()
            self.polygon_h.hide()
            self.progress_h.hide()
            self.progress_v.show()
            
        elif name == 'yn':
            self.polygon_v.setPos(0, new_target*self.PERIOD)
            self.polygon_v.show()   
            self.polygon_h.hide()
            self.progress_h.hide()
            self.progress_v.show()
            

    def next_axis(self):
        self.active_index += 1
        if self.active_index < len(self.axes):
            self.set_value(0)
        else:
            self.calibration_finished.emit()
            self.active_index = -1
            self.set_value(0)
            self.polygon_h.hide()
            self.polygon_v.hide()

        self.__activate_axis__(self.active_index)
        
    def __activate_axis__(self, idx):
        for i in range(len(self.axes)):
            item:QGraphicsItem = self.axes[i]
            pen = item.pen()
            if i == idx:
                pen.setWidth(2)
                pen.setColor(self.COL_SELECTED)
            else:
                pen.setWidth(1)
                pen.setColor(self.COL_NSELECTED)
            
            item.setPen(pen)
    
    def current_axis(self):
        if self.active_index == -1:
            return None
        else:
            return self.axes[self.active_index].objectName
