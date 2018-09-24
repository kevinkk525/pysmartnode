'''
Created on 09.08.2017

@author: Kevin Köck
'''
"""
example config:
{
    package: .multiplexer.amux, #analog multiplexer
    component: Amux
    constructor_args: {
        s0: D5         # muxPin object can be used if an amux is connected to a mux, then mux can be None
        s1: D2         # if all pins are connected to a mux then pin number can be used and mux object has to be given
        s2: D4  
        #s3: null      #optional, if not given a 8-bit amux is used
        mux: null      #optional, if defined then all pins are interpreted as mux pins and have to be integer
        sig: 0          #not needed on esp8266 as it has only one adc anyway, can be an amux pin object (multiple amux)
        return_voltages: false #optional, bool, set true if standard read() should return voltage or false if raw value
    }
}
"""

__updated__ = "2018-08-18"
__version__ = "3.1"

# Version 2.0 should support an Amux connected to an Amux, not tested though, only have one amux

from pysmartnode.components.machine.adc import ADC
import machine
from pysmartnode.components.machine.pin import Pin
from sys import platform
import gc

gc.collect()


class Amux:
    def __init__(self, s0, s1, s2, s3=None, mux=None, sig=None, return_voltages=False):
        """ It is possibile to initialize with:
            - pin numbers (or string on esp8266)
            - mux object and pin numbers (of mux pins)
            - Pin objects (either from machine or mux Pin objects [no mux object needed])
            :type return_voltages: bool, True returns voltages on .read() else raw adc value
            :type mux: Mux object if a multiplexer is used
            :type sig: ADC pin number (esp32) or None (esp8266)
            Amux uses default return values of ADC in .read()
            --> On esp8266 raw, on esp32_LoBo voltage
            s3 is optional, only needed if 16 pins are used, 8 pins possible with s0-s2.
            Amux can be read like a list: value=amux[2]
        """
        if mux:
            self.s0 = s0
            self.s1 = s1
            self.s2 = s2
            self.s3 = s3
            self.mux = mux
        else:
            if type(s0) in (int, str):
                self.s0 = Pin(s0, machine.Pin.OUT)
                self.s1 = Pin(s1, machine.Pin.OUT)
                self.s2 = Pin(s2, machine.Pin.OUT)
                if s3:
                    self.s3 = Pin(s3, machine.Pin.OUT)
            else:
                self.s0 = s0
                self.s1 = s1
                self.s2 = s2
                if s3:
                    self.s3 = s3
        if s3:
            self.__size = 16
        else:
            self.__size = 8
        self._return_voltages = return_voltages
        self.sig = ADC(0 if sig is None and platform == "esp8266" else sig)  # unified ADC interface

    def setReturnVoltages(self, vol):
        self._return_voltages = vol

    def __getitem__(self, a):
        return self.read(a)

    def getSize(self):
        """ Get number of pins"""
        return self.__size

    def read(self, a, return_voltage=None):
        if a >= self.__size:
            raise ValueError("Maximum Port number is {!s}".format(self.__size - 1))
        if type(self.s0) == int:  # mux pins
            if self.__size == 16:
                self.mux[self.s3] = (1 if a & 8 else 0)
            self.mux[self.s2] = (1 if a & 4 else 0)
            self.mux[self.s1] = (1 if a & 2 else 0)
            self.mux[self.s0] = (1 if a & 1 else 0)
            self.mux.write()
        else:
            if self.__size == 16:
                self.s3.value(1 if a & 8 else 0)
            self.s2.value(1 if a & 4 else 0)
            self.s1.value(1 if a & 2 else 0)
            self.s0.value(1 if a & 1 else 0)
        if return_voltage is True or return_voltage is None and self._return_voltages is True:
            return self.sig.readVoltage()
        else:
            return self.sig.readRaw()

    def readVoltage(self, a):
        return self.read(a, return_voltage=True)

    def readRaw(self, a):
        return self.read(a, return_voltage=False)

    def ADC(self, i, *args, **kwargs):
        """ compatible to machine.ADC, returns an ADC object"""
        return ADC(self, i)


class ADC:
    def __init__(self, amux, pin):
        self.__amux = amux
        self.__pin = pin

    def read(self):
        return self.__amux.read(self.__pin)

    def readraw(self):
        return self.__amux.readRaw(self.__pin)

    def readVoltage(self):
        return self.__amux.readVoltage(self.__pin)

    def readRaw(self):
        return self.__amux.readRaw(self.__pin)

    def __str__(self):
        return "amuxPin({!s})".format(self.__pin)
