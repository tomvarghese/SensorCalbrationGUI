from re import S
from typing import Any
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets, QtSerialPort
from PyQt5.QtSerialPort import *  
from PyQt5.QtGui import *  
from PyQt5.QtWidgets import *  
from PyQt5.QtCore import *
from queue import Queue

from qdsp import QDSP

class QADCInterface(QObject):
    block_packets_ready = pyqtSignal(list)
    single_packet_ready = pyqtSignal(tuple)
    results_saved = pyqtSignal(dict)

    def __init__(self, max_packets = 10, parent=None):
        super().__init__(parent)
        self.max_queue = max_packets

class QADCSensor(QSerialPort):
    
    def __init__(self, parent=None, adc_speed = 8):
        super().__init__(parent)
        self.connected = False
        self.bytes = QByteArray()
        self.ADC_SPEED = adc_speed
        # self.buffer = QBuffer()
        # self.buffer.open(QBuffer.ReadWrite)
        self.buffer = []
        self.interface = QADCInterface(max_packets=10, parent=self)

        self.dsp = QDSP(self)
        self.dsp.add_channel('x+',1024*4)
        self.dsp.add_channel('y+',1024*4)
        self.dsp.add_channel('x-',1024*4)
        self.dsp.add_channel('y-',1024*4)

        # self.dsp.set_filter('x', 'maf_fir', order =50)
        # self.dsp.set_filter('y', 'maf_fir', order =50)
        # self.dsp.set_dc_removal('x')
        # self.dsp.set_dc_removal('y')

    def init(self):
        self.write(f'<adc_continuous {self.ADC_SPEED}>\n'.encode())
        self.flush()
        #self.waitForBytesWritten(1000)

    def read_next(self):
        self.write('\n'.encode())

    def turn_off(self):
        self.dsp.set_enabled(False)

    def turn_on(self):
        self.dsp.set_enabled(True)

    def reset_all(self):
        self.dsp.reset()

    def connect(self, port, baudrate):
        self.setPortName(port)
        if self.open(QIODevice.ReadWrite):
            self.setBaudRate(baudrate)
            self.setParity(QSerialPort.Parity.NoParity)
            self.setDataBits(QSerialPort.DataBits.Data8)
            self.setStopBits(QSerialPort.StopBits.OneStop)
            self.readyRead.connect(self.on_serial_read)
            self.init()
            self.connected = True
        else:
            self.connected = False
        
        return self.connected

    def disconnect(self):
        self.connected = False
        self.close()
        return self.connected

    def parse_packet(self,bytes):
        # $CSTLT,-0000.7,-0012.8,+0999.9,-000.03,-000.73,+022*79\r\n
        line = str(bytes, 'utf-8')
        # fields = line.strip().split(',')
        try:
            vals =[float(f) for f in line.strip().split()]
            return tuple(vals)
        except Exception as e:
            pass

    def on_serial_read(self):
        bytes = self.readAll()
        self.bytes += bytes

        
        j = self.bytes.indexOf(b'<')

        while j !=-1:
            self.bytes = self.bytes.mid(j + 1)
            z = self.bytes.indexOf(b'>')
            if z == -1:
                break
                # line=line.remove(z,1)
            line = self.bytes.mid(0,z)


            # if line.endsWith(b'>'):
            #     line=line.remove(line.indexOf('>'),1)

            # if line.startsWith(b'<'):
            line=line.remove(line.indexOf('<'),1)
            packet_xy_xnxy = self.parse_packet(line)
            self.buffer.append(packet_xy_xnxy)
            self.dsp.set_channel('y+',packet_xy_xnxy[0])
            self.dsp.set_channel('x+',packet_xy_xnxy[1])
            self.dsp.set_channel('y-',packet_xy_xnxy[2])
            self.dsp.set_channel('x-',packet_xy_xnxy[3])
            if len(self.buffer) > self.interface.max_queue:
                self.interface.block_packets_ready.emit(self.buffer)
                self.buffer.clear()
            # else:
            #     print("unsync")
            j = self.bytes.indexOf(b'<')

        # if self.connected:
        #     self.read_next()

    def save_results(self, cal_object:dict, type:str):
        axis_to_int = {'y+': 1, 'x+':2, 'y-':3, 'x-':4}
        commands_queue = []

        # composing the commands
        set_type = f'set_type {type}'
        commands_queue.append(set_type)

        for axis, vals in cal_object.items():
            
            command1 = '<SET_CALIB {SENSOR_ID} 1 {Y} {X}>'.format(
                SENSOR_ID = axis_to_int[axis],
                Y = int(vals['points'][0]*100),
                X = int(vals['points'][1])
            )

            command2 = '<SET_CALIB {SENSOR_ID} 2 {Y} {X}>'.format(
                SENSOR_ID = axis_to_int[axis],
                Y = int(vals['points'][2]*100),
                X = int(vals['points'][3])
            )
            commands_queue.append(command1)
            commands_queue.append(command2)
        commands_queue.append('<save>')

        # sending commands
        for command in commands_queue:
            self.write(command.encode())

        self.interface.results_saved.emit({})