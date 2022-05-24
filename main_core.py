import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets, QtSerialPort
from PyQt5.QtSerialPort import *  
from PyQt5.QtGui import *  
from PyQt5.QtWidgets import *  
from PyQt5.QtCore import *
import sys


from main_ui import *
from qserialsensor import *
from qserialadc import *
import os
import glob
from pathlib import Path
from functools import partial
import logging
import pyqtgraph as pg
import numpy as np
from qregression import *

class MainWindow(QtWidgets.QMainWindow):
    
    def __init__(self,app) :
        super(MainWindow,self).__init__()
        self.ui = Ui_MainWindow()
        # setup the ui
        self.ui.setupUi(self)
        self.app=app
        self.prepare_serial()
        self.prepare_fitters()
        self.prepare_plots()
        self.run_defaults()
        self.do_connections()
        

    def do_connections(self):
        self.ui.btn_refresh.clicked.connect(self.update_com_ports)
        self.ui.btn_refresh_adc.clicked.connect(self.update_com_ports)

        self.ui.btn_start.clicked.connect(self.start_serial)
        self.ui.btn_stop.clicked.connect(self.stop_serial)

        self.ui.btn_start_adc.clicked.connect(self.start_serial_adc)
        self.ui.btn_stop_adc.clicked.connect(self.stop_serial_adc)

        self.sensor.interface.block_packets_ready.connect(self.on_packet_block_ready)
        self.adc.interface.block_packets_ready.connect(self.on_packet_block_ready_adc)

        self.ui.btn_plot_xy.clicked.connect(self.enable_xy_plots)
        self.xy_timer.timeout.connect(self.plot_xy)

    def prepare_plots(self):
        self.curve_x = pg.PlotCurveItem(pen='r')
        self.curve_y = pg.PlotCurveItem(pen='g')

        self.curve_xp = pg.PlotCurveItem(pen='b')
        self.curve_yp = pg.PlotCurveItem(pen='c')
        self.curve_xn = pg.PlotCurveItem(pen='m')
        self.curve_yn = pg.PlotCurveItem(pen='k')

        self.curve_XY_xp = pg.ScatterPlotItem(pen='r',size=2)
        self.curve_XY_xn = pg.PlotCurveItem(pen='r')
        self.curve_XY_yp = pg.PlotCurveItem(pen='r')
        self.curve_XY_yn = pg.PlotCurveItem(pen='r')

        self.ui.plot_widget.addItem(self.curve_x)
        self.ui.plot_widget.addItem(self.curve_y)

        self.ui.plot_widget.addItem(self.curve_xp)
        self.ui.plot_widget.addItem(self.curve_yp)
        self.ui.plot_widget.addItem(self.curve_xn)
        self.ui.plot_widget.addItem(self.curve_yn)

        self.ui.plot_widget_xp.addItem(self.curve_XY_xp)
        self.ui.plot_widget_xn.addItem(self.curve_XY_xn)
        self.ui.plot_widget_yp.addItem(self.curve_XY_yp)
        self.ui.plot_widget_yn.addItem(self.curve_XY_yn)
       

        self.ui.plot_widget_xp.setYRange(min = -30, max = 30)
        self.ui.plot_widget_xp.setXRange(min = 500, max = 2500)

    def run_defaults(self):
        self.update_com_ports()
        self.ui.text_baudrate.setText('115200')
        self.ui.text_baudrate_adc.setText('115200')
        self.connected = False
        self.connected_adc = False

        self.enabled_xy = False
        self.xy_timer = QTimer()
        self.xy_timer.setInterval(20)

    def update_com_ports(self):
        self.ui.combo_ports.clear()
        self.ui.combo_ports_adc.clear()
        logging.debug("Updaing COM ports")

        com_ports=QSerialPortInfo.availablePorts()
        for com_port in com_ports:
            port_name = com_port.portName()
            self.ui.combo_ports.addItem(port_name)
            self.ui.combo_ports_adc.addItem(port_name)

    def prepare_serial(self):
        self.sensor = QSerialSensor()
        self.adc = QADCSensor()

    def prepare_fitters(self):
        self.fit_core = QRegression()

    def start_serial(self):
        if self.connected:
            return
        port = self.ui.combo_ports.currentText().strip()
        baudrate = int(self.ui.text_baudrate.text().strip())
        
        self.connected = self.sensor.connect(port=port, baudrate=baudrate)
        if self.connected:
            pass
    
    def stop_serial(self):
        if not self.connected:
            return
        self.connected = self.sensor.disconnect()

    def start_serial_adc(self):
        if self.connected_adc:
            return
        port = self.ui.combo_ports_adc.currentText().strip()
        baudrate = int(self.ui.text_baudrate_adc.text().strip())
        
        self.connected_adc = self.adc.connect(port=port, baudrate=baudrate)
        if self.connected_adc:
            pass
    
    def stop_serial_adc(self):
        if not self.connected_adc:
            return
        self.connected_adc = self.adc.disconnect()

    def on_packet_block_ready_adc(self,blocks:list):
        xp,t0 = self.adc.dsp.get_channel('x+')
        yp,t1 = self.adc.dsp.get_channel('y+')
        xn,t2 = self.adc.dsp.get_channel('x-')
        yn,t3 = self.adc.dsp.get_channel('y-')
        self.curve_xp.setData(xp)
        self.curve_yp.setData(yp)
        self.curve_xn.setData(xn)
        self.curve_yn.setData(yn)

    def on_packet_block_ready(self,blocks:list):
        sensor_x,t = self.sensor.dsp.get_channel("x")
        sensor_y,t = self.sensor.dsp.get_channel("y")
        self.curve_x.setData(sensor_x)
        self.curve_y.setData(sensor_y)
        #for (x,y) in blocks:
        #   print(f"Packet x:{x} y:{y}")
    
    def enable_xy_plots(self):
        if self.enabled_xy:
            self.enabled_xy = False
            self.xy_timer.stop()
            self.curve_XY_xp.clear()
        else:
            self.enabled_xy = True
            self.xy_timer.start()

    def plot_xy(self):
        # sensor_b = 615+np.random.choice([0, 1], size=(100,))
        # sensor_a = 415+np.random.choice(np.arange(-1,1,0.2), size=(100,))
        
        sensor_a, ta =  self.sensor.dsp.get_channel('x')
        sensor_b, tb = self.adc.dsp.get_channel('x+')
        self.curve_XY_xp.setData(sensor_b,sensor_a)

        # m, c = self.fit_core.linear_fit(sensor_b,sensor_a)
        # b_testdata = np.arange(610,630,1)
        # a_fit = m*b_testdata+c
        # a_fit = a_fit.reshape((len(b_testdata)))
        # self.curve_XY_xn.setData(b_testdata,a_fit)
        # print('--')
