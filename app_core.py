# V1.1
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets, QtSerialPort
from PyQt5.QtSerialPort import *  
from PyQt5.QtGui import *  
from PyQt5.QtWidgets import *  
from PyQt5.QtCore import *
import sys

from enum import Enum
import matplotlib.pyplot as plt

from app_ui import *
from qserialsensor import *
from qserialadc import *
import os
import json
from pathlib import Path
from functools import partial
import logging
import pyqtgraph as pg
import numpy as np
from qregression import *
from dataclasses import dataclass

TEST = False
logging.getLogger('matplotlib').setLevel(logging.ERROR)

@dataclass 
class SerialSettings:
    baudrate: int = 115200

class ui_pages(Enum):
    page_welcome = 0
    page_sensors_config = 1
    page_confirm_sensors = 2
    page_dc_cancel = 3
    page_calibrate_xp = 4
    page_calibrate_yp = 5
    page_calibrate_xn = 6
    page_calibrate_yn = 7
    page_calibration_results = 8
    page_saving_calibration = 9

class CalibrationFSM(QObject):
    signal_calibration_started = pyqtSignal()
    signal_calibration_ended = pyqtSignal()
    signal_calibration_target_moved =  pyqtSignal(float) # new target
    signal_calibration_channel_finished = pyqtSignal(str) # finished channel


    def __init__(self):
        super().__init__()
        try:
            with open('config.json', 'r') as f:
                data = json.load(f)

            self.target_points = data['checkpoints']
        except Exception as e:
            self.target_points = [5, 10, 20]

        self.calibration_channels =['x+', 'y+', 'x-', 'y-']
        self.current_channel = -1
        self.current_target = -1
        self.started = False
        self.threshold = 10
        
        self.xp = {'sensor':None, 'adc':None, 'cal_coeff':[], 'adc_max':0, 'adc_min':0}
        self.yp = {'sensor':None, 'adc':None, 'cal_coeff':[], 'adc_max':0, 'adc_min':0}
        self.xn = {'sensor':None, 'adc':None, 'cal_coeff':[], 'adc_max':0, 'adc_min':0}
        self.yn = {'sensor':None, 'adc':None, 'cal_coeff':[], 'adc_max':0, 'adc_min':0}

        self.calibrations = {}
        self.calibrations['x+'] = self.xp
        self.calibrations['y+'] = self.yp
        self.calibrations['x-'] = self.xn
        self.calibrations['y-'] = self.yn
    
    def start_calibration(self, channel=''):
        self.current_channel = 0
        self.current_target = 0
        self.started = True
        self.signal_calibration_started.emit()

    def target(self):
        return self.target_points[self.current_target] if self.current_target != -1 else None
    
    def channel(self):
        return self.calibration_channels[self.current_channel] if self.current_channel != -1 else None

    def to_next_target(self):
        if self.current_target < len(self.target_points)-1:
            self.current_target += 1
            self.signal_calibration_target_moved.emit(self.target())
        else:
            # we will move ot next channel
            chan = self.channel()
            self.to_next_channel()
            self.signal_calibration_channel_finished.emit(chan)
            

        return self.current_target

    def to_next_channel(self):
        if self.current_channel < len(self.calibration_channels)-1:
            self.current_channel += 1
            self.current_target = 0
        else:
            self.signal_calibration_ended.emit()
            self.started = False
         
class MainWindow(QtWidgets.QMainWindow):
    
    def __init__(self,app) :
        super(MainWindow,self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.app=app

        self.settings = SerialSettings()
        self.cal = CalibrationFSM()
        self.fitter = QRegression(None,self.cal)

        self.adc_connected = False
        self.sensor_connected = False
        self.channels_offset_removed = []
        self.offsets_removed = False

        self.prepare_serial()
        # self.prepare_fitters()
        self.prepare_plots()
        self.run_defaults()
        self.prepare_serial()
        self.do_connections()
        
        if TEST:
            self.__test_init__()

    def prepare_serial(self):
        self.sensor = QSerialSensor()
        self.adc = QADCSensor()

    def update_com_ports(self):
        self.ui.combo_adc_port.clear()
        self.ui.combo_sensor_port.clear()
        logging.debug("Updaing COM ports")

        com_ports=QSerialPortInfo.availablePorts()
        for com_port in com_ports:
            port_name = com_port.portName()
            self.ui.combo_adc_port.addItem(port_name)
            self.ui.combo_sensor_port.addItem(port_name)

    def do_connections(self):
        self.ui.btn_next.clicked.connect(self.proceed)
        self.ui.btn_refresh.clicked.connect(self.update_com_ports)
        self.ui.btn_rese_cal.clicked.connect(lambda x: self.go_to_page(ui_pages.page_confirm_sensors))

        self.sensor.interface.block_packets_ready.connect(self.__confirm_plot_sensor_readings__)
        self.adc.interface.block_packets_ready.connect(self.__confirm_plot_adc_readings__)

        self.sensor.dsp.interface.dc_offse_cancled.connect(self.__dsp_dc_offset_removed__)

        self.cal.signal_calibration_channel_finished.connect(self.__calibration_channel_finished__)
        self.cal.signal_calibration_target_moved.connect(self.__calibration_target_moved__)

        self.adc.interface.results_saved.connect(self.__results_saved__)

    def prepare_plots(self):
        self.ui.plot_xyn.setBackground(QtGui.QColor('white'))
        self.ui.plot_xyp.setBackground(QtGui.QColor('white'))
        self.ui.plot_xyref.setBackground(QtGui.QColor('white'))

        self.ui.plot_cal_xp.setBackground(QtGui.QColor('white'))
        self.ui.plot_cal_xn.setBackground(QtGui.QColor('white'))
        self.ui.plot_cal_yn.setBackground(QtGui.QColor('white'))
        self.ui.plot_cal_yp.setBackground(QtGui.QColor('white'))

        # self.ui.plot_clibrate.setBackground(QtGui.QColor('white'))

        self.ui.plot_xyn.plotItem.showGrid(x=True, y=True, alpha=1)
        self.ui.plot_xyp.plotItem.showGrid(x=True, y=True, alpha=1)
        self.ui.plot_xyref.plotItem.showGrid(x=True, y=True, alpha=1)

        self.ui.plot_cal_xp.plotItem.showGrid(x=True, y=True, alpha=1)
        self.ui.plot_cal_xn.plotItem.showGrid(x=True, y=True, alpha=1)
        self.ui.plot_cal_yn.plotItem.showGrid(x=True, y=True, alpha=1)
        self.ui.plot_cal_yp.plotItem.showGrid(x=True, y=True, alpha=1)

        # self.ui.plot_clibrate.plotItem.showGrid(x=True, y=True, alpha=1)
        
        self.ui.plot_xyn.plotItem.showButtons()
        self.ui.plot_xyp.plotItem.showButtons()
        self.ui.plot_xyref.plotItem.showButtons()

        self.ui.plot_cal_xp.plotItem.showButtons()
        self.ui.plot_cal_xn.plotItem.showButtons()
        self.ui.plot_cal_yn.plotItem.showButtons()
        self.ui.plot_cal_yp.plotItem.showButtons()
        # self.ui.plot_clibrate.plotItem.showButtons()
        
        self.ui.plot_xyn.plotItem.layout.setContentsMargins(0,0,0,0)
        self.ui.plot_xyp.plotItem.layout.setContentsMargins(0,0,0,0)
        self.ui.plot_xyref.plotItem.layout.setContentsMargins(0,0,0,0)
        # self.ui.plot_clibrate.plotItem.layout.setContentsMargins(0,0,0,0)


        self.curve_x = pg.PlotCurveItem(pen='r')
        self.curve_y = pg.PlotCurveItem(pen='g')

        self.curve_xp = pg.PlotCurveItem(pen='b')
        self.curve_yp = pg.PlotCurveItem(pen='c')

        self.curve_xn = pg.PlotCurveItem(pen='m')
        self.curve_yn = pg.PlotCurveItem(pen='k')



        self.curve_cal_result_xp = pg.PlotCurveItem(pen='b')
        self.curve_cal_result_yp = pg.PlotCurveItem(pen='b')
        self.curve_cal_result_xn = pg.PlotCurveItem(pen='b')
        self.curve_cal_result_yn = pg.PlotCurveItem(pen='b')

        self.ui.plot_xyref.addItem(self.curve_x)
        self.ui.plot_xyref.addItem(self.curve_y)

        self.ui.plot_xyp.addItem(self.curve_xp)
        self.ui.plot_xyp.addItem(self.curve_yp)

        self.ui.plot_xyn.addItem(self.curve_xn)
        self.ui.plot_xyn.addItem(self.curve_yn)

        self.ui.plot_cal_xp.addItem(self.curve_cal_result_xp)
        self.ui.plot_cal_yp.addItem(self.curve_cal_result_yp)
        self.ui.plot_cal_xn.addItem(self.curve_cal_result_xn)
        self.ui.plot_cal_yn.addItem(self.curve_cal_result_yn)

        # scatter plot
        self.curve_cal_xp_scatter= pg.ScatterPlotItem(pen='r',size=2)
        self.curve_cal_yp_scatter= pg.ScatterPlotItem(pen='r',size=2)
        self.curve_cal_xn_scatter= pg.ScatterPlotItem(pen='r',size=2)
        self.curve_cal_yn_scatter= pg.ScatterPlotItem(pen='r',size=2)

        self.ui.plot_cal_xp.addItem(self.curve_cal_xp_scatter)
        self.ui.plot_cal_yp.addItem(self.curve_cal_yp_scatter)
        self.ui.plot_cal_xn.addItem(self.curve_cal_xn_scatter)
        self.ui.plot_cal_yn.addItem(self.curve_cal_yn_scatter)

    def run_defaults(self):
        try:
            with open('config.json', 'r') as f:
                data = json.load(f)

            types = data['types']

        except Exception as e:
            types = [ "21-04227", "21-04122", "21-04070", "22-04416", "21-03929"]
        
        self.ui.combo_type.addItems(types)
            
        self.go_to_page(ui_pages.page_sensors_config)
        # self.go_to_page(ui_pages.page_calibrate_)

    def go_to_page(self, target_page):
        self.ui.stackedWidget.setCurrentIndex(target_page.value)
        # Dynamic GUI
        self.dynamic_gui()

        # Dynamic parts
        if target_page == ui_pages.page_dc_cancel:
            self.start_offset_cancellation()
        
        elif target_page == ui_pages.page_sensors_config:
            self.update_com_ports()

        elif target_page == ui_pages.page_confirm_sensors:
            pass
        
        elif target_page == ui_pages.page_calibrate_xp:
            self.__calibration_start_xp__()
        
        elif target_page == ui_pages.page_calibrate_yp:
            self.__calibration_start_yp__()

        elif target_page == ui_pages.page_calibrate_xn:
            self.__calibration_start_xn__()
        
        elif target_page == ui_pages.page_calibrate_yn:
            self.__calibration_start_yn__()
        
        elif target_page == ui_pages.page_calibration_results:
            self.__populate_calibration_graphs__()
        
        elif target_page == ui_pages.page_saving_calibration:
            self.__save_calibration_results__()
                     
    def dynamic_gui(self):
        idx = self.ui.stackedWidget.currentIndex()
        current_page = ui_pages(idx)

        if current_page != ui_pages.page_sensors_config:
            self.ui.btn_refresh.hide()
        else:
            self.ui.btn_refresh.show()
        
        if current_page == ui_pages.page_dc_cancel:
            self.ui.btn_next.hide()
        
        if current_page == ui_pages.page_calibration_results:
            self.ui.btn_next.setText('Finish')
        else:
            self.ui.btn_next.setText('Next')
       
    def proceed(self):
        idx = self.ui.stackedWidget.currentIndex()
        current_page = ui_pages(idx)

        if current_page == ui_pages.page_sensors_config:
            self.__start_serial_sensor__()
            self.__start_serial_adc__()
            if self.adc_connected and self.sensor_connected:
                target_page = ui_pages.page_confirm_sensors
            
            else:
                # Error
                return
        elif current_page == ui_pages.page_saving_calibration:
            target_page = ui_pages.page_welcome

        else:
            if idx+1 >=len(ui_pages):
                return
        
            target_page = ui_pages(idx+1)

        self.go_to_page(target_page)

    def start_offset_cancellation(self):
        print('starting dc offset cancelation')
        self.sensor.dsp.set_dc_removal('x')
        self.sensor.dsp.set_dc_removal('y')

    # DSP-GUI related work
    def __dsp_dc_offset_removed__(self, channel):
        self.channels_offset_removed.append(channel)
        if 'x' in self.channels_offset_removed and 'y' in self.channels_offset_removed :
            self.offsets_removed = True
            self.ui.btn_next.show()
        else:
            self.offsets_removed = False

    # Serial ports work
    def __start_serial_sensor__(self):
        if self.sensor_connected:
            return
        port = self.ui.combo_sensor_port.currentText().strip()
        baudrate = self.settings.baudrate# int(self.ui.text_baudrate.text().strip())
        
        self.sensor_connected = self.sensor.connect(port=port, baudrate=baudrate)
        if self.sensor_connected:
            pass
    
    def __start_serial_adc__(self):
        if self.adc_connected:
            return
        port = self.ui.combo_adc_port.currentText().strip()
        baudrate = self.settings.baudrate
        
        self.adc_connected = self.adc.connect(port=port, baudrate=baudrate)
        if self.adc_connected:
            pass

    def __confirm_plot_sensor_readings__(self, blocks):
        if not self.cal.started:
            sensor_x,t = self.sensor.dsp.get_channel("x")
            sensor_y,t = self.sensor.dsp.get_channel("y")

            self.curve_x.setData(sensor_x)
            self.curve_y.setData(sensor_y)
        else:
            # This means we are in calibration mode. so, we will forward the reading to the
            # calibration progressbar
            xreading, yreading = abs(blocks[-1][0]), abs(blocks[-1][1])
            channel = self.cal.channel()
            reading = xreading if channel.startswith('x') else yreading

            # getting the approperiate progress bar
            if channel == 'x+':
                progress = self.ui.progressBar_xp
            elif channel == 'y+':
                progress = self.ui.progressBar_yp
            elif channel == 'x-':
                progress = self.ui.progressBar_xn
            elif channel == 'y-':
                progress = self.ui.progressBar_yn

            progress.setValueF(reading)
            self.__calibration_step__(reading, channel, progress)

    def __confirm_plot_adc_readings__(self, blocks):
        if not self.cal.started:
            xp,t0 = self.adc.dsp.get_channel('x+')
            yp,t1 = self.adc.dsp.get_channel('y+')
            xn,t2 = self.adc.dsp.get_channel('x-')
            yn,t3 = self.adc.dsp.get_channel('y-')

            self.curve_xp.setData(xp)
            self.curve_yp.setData(yp)

            self.curve_xn.setData(xn)
            self.curve_yn.setData(yn)

    # Calibration work
    def __calibration_start_xp__(self):
        self.ui.btn_next.hide()
        self.cal.start_calibration()
        target = self.cal.target()
        self.ui.progressBar_xp.set_target(target)

        # reseting all dsp channels and turning them off
        # we will turn on them one by one
        self.sensor.dsp.reset()
        self.sensor.dsp.set_enabled('all',False)
        self.sensor.dsp.set_monotonic('x', increasing=True)

        self.adc.dsp.reset()
        self.adc.dsp.set_enabled('all',False)

        logging.debug(f"Calibration Process started for X+")

    def __calibration_start_yp__(self):
        # self.cal.start_calibration()
        self.ui.btn_next.hide()
        target = self.cal.target()
        self.ui.progressBar_yp.set_target(target)

        # reseting all dsp channels and turning them off
        # we will turn on them one by one
        self.sensor.dsp.reset()
        self.sensor.dsp.set_enabled('all',False)
        
        self.adc.dsp.reset()
        self.adc.dsp.set_enabled('all',False)

        logging.debug(f"Calibration Process started for Y+")

    def __calibration_start_xn__(self):
        # self.cal.start_calibration()
        self.ui.btn_next.hide()
        target = self.cal.target()
        self.ui.progressBar_xn.set_target(target)

        # reseting all dsp channels and turning them off
        # we will turn on them one by one
        self.sensor.dsp.reset()
        self.sensor.dsp.set_enabled('all',False)
        
        self.adc.dsp.reset()
        self.adc.dsp.set_enabled('all',False)

        logging.debug(f"Calibration Process started for X-")
    
    def __calibration_start_yn__(self):
        # self.cal.start_calibration()
        self.ui.btn_next.hide()
        target = self.cal.target()
        self.ui.progressBar_yn.set_target(target)

        # reseting all dsp channels and turning them off
        # we will turn on them one by one
        self.sensor.dsp.reset()
        self.sensor.dsp.set_enabled('all',False)
        
        self.adc.dsp.reset()
        self.adc.dsp.set_enabled('all',False)

        logging.debug(f"Calibration Process started for Y-")

    def __calibration_step__(self, reading, channel, progressbar):
        if not self.cal.started:
            return
        
        # check if we've reached the target, move to the next
        if  self.cal.target() - reading < 0.1:
            self.cal.to_next_target()
            target = self.cal.target()
            if channel == self.cal.channel():
                progressbar.set_target(target)
            else:
                # This means we are moving to next channel
                return

        # check if we've reached capturing zone (target-threshold), enable the dsp (adc and sensor)
        if self.cal.target() - reading < self.cal.threshold:
            self.sensor.dsp.set_enabled(channel[0], True)
            self.adc.dsp.set_enabled(channel, True)
        else:
            self.sensor.dsp.set_enabled(channel[0], False)
            self.adc.dsp.set_enabled(channel, False)

    def __calibration_channel_finished__(self, channel):
        # do its calibration work
        logging.debug(f"Fitting for channel={channel} started")
        # capturing sensor data
        sensor_data,t_sensor = self.sensor.dsp.get_channel(channel[0], deepcopy=True)
        # capturing adc data
        adc_data, t_adc = self.adc.dsp.get_channel(channel, deepcopy=True)
        # saving them
        if channel == 'x+':
            obj = self.cal.xp
        elif channel == 'x-':
            obj = self.cal.xn
        elif channel == 'y+':
            obj = self.cal.yp
        else:
            obj = self.cal.yn
        
        # ensuring monotonic
        # if channel[-1] =='+':
        #     sensor_data = np.maximum.accumulate(sensor_data)
        # else:
        #     sensor_data = np.minimum.accumulate(sensor_data)

        

        # getting unqiue 
        condition = sensor_data > 5 if channel[-1] =='+' else sensor_data < -5
        sensor_data_unique, unique_idx = np.unique(sensor_data[condition], return_index=True)
        adc_data_unique = adc_data[condition][unique_idx]
        
        obj['sensor'] = sensor_data_unique
        obj['adc'] = adc_data_unique
        obj['adc_max'] = adc_data.max()
        obj['adc_min'] = adc_data.min()
        # curve fitting
        m,c = self.fitter.linear_fit(adc_data_unique, sensor_data_unique)
        obj['cal_coeff'] = m, c

        xmin, xmax = obj['adc_min'], obj['adc_max']
        ymin, ymax = (m*xmin)+c, (m*xmax)+c
        obj['points'] = [ymin, xmin, ymax, xmax]
        self.cal.calibrations[channel] = obj

        logging.debug(f"Fitting for channel={channel} done")
        self.ui.btn_next.show()

    def __calibration_target_moved__(self, target):
        # disable all again
        self.sensor.dsp.set_enabled('all', False)
        self.adc.dsp.set_enabled('all', False)
        logging.debug(f"Target moved to {target}")

    def __populate_calibration_graphs__(self):
        
        for k,v in self.cal.calibrations.items():
            # actual data
            sensor_data = v['sensor']
            adc_data = v['adc']

            # generate x data (ADC)
            adc_min = v['adc_min']
            adc_max = v['adc_max']
            x_data = np.arange(max(adc_min-5,0),min(adc_max+5, 4096),1)
            # calculate y data
            m,c = v['cal_coeff']
            y_data = m*x_data+c
            y_data = y_data.reshape((len(x_data)))

            # plot
            if k == 'xp':
                curve = self.curve_cal_result_xp
                scatter = self.curve_cal_xp_scatter
            elif k == 'yp':
                curve = self.curve_cal_result_yp
                scatter = self.curve_cal_yp_scatter
            elif k == 'xn':
                curve = self.curve_cal_result_xn
                scatter = self.curve_cal_xn_scatter
            else:
                curve = self.curve_cal_result_yn
                scatter = self.curve_cal_yn_scatter
        
            curve.setData(x_data,y_data)
            scatter.setData(adc_data,sensor_data)

    def __save_calibration_results__(self):
        self.ui.btn_next.hide()
        type = self.ui.combo_type.currentText()
        self.adc.save_results(self.cal.calibrations, type)
    
    def __results_saved__(self, args={}):
        self.ui.btn_next.show()
        # reset everything


    # Testing functions
    def __test_init__(self):
        self.msg_start_calibration = QShortcut(QKeySequence('Ctrl+Q'), self)
        self.msg_start_calibration.activated.connect(self.__calibration_start__)

        self.msg_move_calibration_p = QShortcut(QKeySequence('Ctrl+S'), self)
        self.msg_move_calibration_p.activated.connect(lambda: self.__test_angle_move__(1))

        self.msg_move_calibration_p = QShortcut(QKeySequence('Ctrl+A'), self)
        self.msg_move_calibration_p.activated.connect(lambda: self.__test_angle_move__(-1))

        self.ui.progressBar_xp.setValueF(0)
    
    def __test_angle_move__(self, dir=1):
        step = 0.2 * dir
        value = self.ui.progressBar_xp.valueF()
        if self.ui.progressBar_xp.minimum() <= value+step <= self.ui.progressBar_xp.maximum():
            self.ui.progressBar_xp.setValueF(value+step)
            if abs(value+step - self.cal.target())<0.1:
                self.cal.to_next_target() 
                target = self.cal.target()
                self.ui.progressBar_xp.set_target(target)

