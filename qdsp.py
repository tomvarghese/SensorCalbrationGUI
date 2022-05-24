# V1.1
import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets, QtSerialPort
from PyQt5.QtSerialPort import *  
from PyQt5.QtGui import *  
from PyQt5.QtWidgets import *  
from PyQt5.QtCore import *
import numpy as np
from numpy.core.fromnumeric import argsort
from scipy.ndimage import shift


class QDSPInterface(QObject):
    dc_offse_cancled = pyqtSignal(str)


class QDSP(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.channels = {}
        self.time_axis = {}
        self.filtered = {}
        self.filter = {}
        self.args = {}
        self.sample_counter = {}
        self.dc_remove = {}
        self.dc_offset = {}
        self.max_window = 100
        self.enabled = {}
        self.interface = QDSPInterface()

        self.monotonic = {}
        self.increasing_only = False
        

    def add_channel(self, channel, max_window=100):
        self.max_window = max_window
        self.channels[channel] = {'raw':np.zeros((max_window,), dtype=float)}
        self.time_axis[channel] = np.arange(max_window, dtype=float)
        self.sample_counter[channel] = 0
        self.dc_remove[channel] = False
        self.dc_offset[channel] = np.nan
        self.enabled[channel] = True
        self.monotonic[channel] = None
        
    def get_channel(self,channel, deepcopy = False):
        arr = self.channels[channel].get('filtered', None)
        if arr is None:
            arr = self.channels[channel].get('raw', None)

        t = self.time_axis.get(channel, None)
        return np.copy(arr) if deepcopy else arr, t

    def set_channel(self, channel:str, val):
        if not self.enabled[channel]:
            r_val = val - self.dc_offset[channel] if self.dc_remove.get(channel, False) else val
            return r_val
        
        r_val = val
        n = len(val) if type(val) == list else 1
        self.sample_counter[channel] +=1
        if n == 1:
            if self.channels[channel].get('request_dc_remove', False):
                self.remove_dc(channel)
                val = val - self.dc_offset[channel] if self.dc_remove.get(channel, False) else val
                r_val = val
            self.channels[channel]['raw'] = shift(self.channels[channel]['raw'], -n, cval=val)
            # filtering
            if self.filtered.get(channel, False):
                if self.filter[channel] == 'maf_fir':
                    r_val = self.maf_filter_fir(channel, val)
                    

        else:
            self.channels[channel]['raw'] = shift(self.channels[channel]['raw'], -n, cval=np.nan)
            for i in range(n):
                self.channels[channel][1,-(n+1)] = val[-(n+1)]
        return r_val

    def set_filter(self, channel, type='maf_fir',**kargs):
        self.filtered[channel] = True
        self.filter[channel] = type
        max_window = self.channels[channel]['raw'].shape
        self.channels[channel]['filtered'] = np.zeros(max_window, dtype=float)
        self.args = kargs
    


    def maf_filter_fir(self, channel, val):
        order = self.args['order']
        fval = np.average(self.channels[channel]['raw'][-order:])
        self.channels[channel]['filtered'] = shift(self.channels[channel]['filtered'], -1, cval=fval)
        return fval

    def set_dc_removal(self, channel):
        self.channels[channel]['request_dc_remove'] = True

    def remove_dc(self, channel):    
        if not self.channels[channel]['request_dc_remove']:
            return
            
        target =  self.channels[channel]['raw']# self.channels[channel]['filtered'] if self.filtered.get(channel, False) else self.channels[channel]['raw']
        N_SAMPLES = target.shape[-1]//2

        if self.sample_counter[channel] < N_SAMPLES:
            self.dc_remove[channel] = False
            return

        elif self.dc_remove[channel]:
            return

        else:
            dc = np.average(target[-N_SAMPLES:])
            print(f"Removing dc offset of {dc}")
            self.dc_offset[channel] = dc
            self.dc_remove[channel] = True
            self.channels[channel]['request_dc_remove'] = False
            self.interface.dc_offse_cancled.emit(channel)

    def reset(self):
        for channel, v in self.channels.items():
            
            self.sample_counter[channel] = 0
            self.monotonic[channel] = None
            # self.dc_remove[channel] = False
            # self.dc_offset[channel] = np.nan
            # self.filtered[channel] = False

            v['raw'] = np.zeros((self.max_window,), dtype=float)
            arr = v.get('filtered', None)

            if arr is not None:
                v['filtered'] = np.zeros((self.max_window,), dtype=float)
            
            # if v.get('request_dc_remove', False):
            #     v['filtered'] = False

    def set_enabled(self, channel, is_enabled=True):
        if channel == 'all':
            for k,v in self.channels.items():
                self.enabled[k] = is_enabled
        else:
            self.enabled[channel] = is_enabled
    
    def set_monotonic(self, channel, **kwargs):
        if 'increasing' in kwargs.keys():
            self.monotonic[channel] = 'increasing'
        elif 'decreasing' in kwargs.keys():
            self.monotonic[channel] = 'decreasing'
        elif 'off' in kwargs.keys():
            self.monotonic[channel] = None