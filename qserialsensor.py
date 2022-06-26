from typing import Any
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets, QtSerialPort
from PyQt5.QtSerialPort import *  
from PyQt5.QtGui import *  
from PyQt5.QtWidgets import *  
from PyQt5.QtCore import *
from queue import Queue

from qdsp import QDSP

class QSensorInterface(QObject):
    block_packets_ready = pyqtSignal(list)
    single_packet_ready = pyqtSignal(tuple)

    def __init__(self, max_packets = 10, parent=None):
        super().__init__(parent)
        self.max_queue = max_packets

class QSerialSensor(QSerialPort):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connected = False
        self.bytes = QByteArray()
        
        # self.buffer = QBuffer()
        # self.buffer.open(QBuffer.ReadWrite)
        self.buffer = []
        self.interface = QSensorInterface(max_packets=10, parent=self)

        self.dsp = QDSP(self)
        self.dsp.add_channel('x',1024*4)
        self.dsp.add_channel('y',1024*4)

        self.dsp.set_filter('x', 'maf_fir', order =50)
        self.dsp.set_filter('y', 'maf_fir', order =50)
        
        # self.dsp.set_dc_removal('x')
        # self.dsp.set_dc_removal('y')

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
       
        # fields = line.strip().split(',')
        try:
            line = str(bytes, 'utf-8')
            vals =[float(f) for f in line.strip().split(',')[1:-1]]
            return (vals[-2],vals[-1])
        except Exception as e:
            return None


    def on_serial_read(self):
        bytes = self.readAll()
        self.bytes += bytes

        j = self.bytes.indexOf(b'\n')
        while j !=-1:
            line = self.bytes.mid(0,j)
            z = line.indexOf('\r')
            if z >-1:
                line=line.remove(z,1)

            self.bytes.remove(0,j+1)

            if line.startsWith(b'$CSTLT'):
                packet_xy = self.parse_packet(line)
                
                x = self.dsp.set_channel('x',packet_xy[0])
                y = self.dsp.set_channel('y',packet_xy[1])
                packet_xy = (x,y)
                self.buffer.append(packet_xy)

                if len(self.buffer) > self.interface.max_queue:
                    self.interface.block_packets_ready.emit(self.buffer)
                    self.buffer.clear()
            else:
                print("unsync")
            j = self.bytes.indexOf(b'\n')

        #PACKET_SIZE = 58
        #stream_length = self.bytesAvailable()
        #left = stream_length % PACKET_SIZE
        #n_complete_packets =  stream_length - left

        #if n_complete_packets == 0:
        #    return

        #bytes = self.read(n_complete_packets*PACKET_SIZE)
        #for i in range(0, len(bytes),PACKET_SIZE):
        #    packet_xy = self.parse_packet(bytes[i:i+PACKET_SIZE])
        #    self.buffer.append(packet_xy)
        #    if len(self.buffer) > self.interface.max_queue:
        #        self.interface.block_packets_ready.emit(self.buffer)
        #        self.buffer.clear()
        #
        #self.buffer.write(bytes)