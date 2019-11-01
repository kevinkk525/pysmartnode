# Author: Kevin Köck
# Copyright Kevin Köck 2017-2019 Released under the MIT license
# Created on 2017-08-09

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

__updated__ = "2019-04-03"
__version__ = "3.3"

# Version 2.0 should support an Amux connected to an Amux, not tested though, only have one amux

from pysmartnode.components.machine.adc import ADC as _ADC, pyADC as _pyADC
import machine
from pysmartnode.components.machine.pin import Pin
import gc

gc.collect()


class Amux:
    def __init__(self, s0, s1, s2, s3=None, mux=None, adc=None, return_voltages=False):
        """ It is possibile to initialize with:
            - pin numbers (or string on esp8266)
            - mux object and pin numbers (of mux pins)
            - Pin objects (either from machine or mux Pin objects [no mux object needed], or Arduino)
            :type return_voltages: bool, True returns voltages on .read() else raw adc value
            :type mux: Mux object if a multiplexer is used
            :type adc: ADC pin number (esp32) or None (esp8266) or Arduino ADC object or any ADC object
            Amux uses default return values of ADC in .read()
            --> On esp8266/esp32 raw, on esp32_LoBo voltage
            s3 is optional, only needed if 16 pins are used, 8 pins possible with s0-s2.
            Amux can be read like a list: value=amux[2]
        """
        if mux:
            # MUX pin numbers, not pin objects
            self._s0 = s0
            self._s1 = s1
            self._s2 = s2
            self._s3 = s3
            self._mux = mux
        else:
            # Pin will take care of returning the correct object
            self._s0 = Pin(s0, machine.Pin.OUT)
            self._s1 = Pin(s1, machine.Pin.OUT)
            self._s2 = Pin(s2, machine.Pin.OUT)
            if s3:
                self._s3 = Pin(s3, machine.Pin.OUT)
        if s3:
            self.__size = 16
        else:
            self.__size = 8
        self._return_voltages = return_voltages
        self._adc = _ADC(
            adc)  # no matter what adc is, _ADC will return an object with the unified ADC API

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
        if type(self._s0) == int:  # mux pins
            if self.__size == 16:
                self._mux[self._s3] = (1 if a & 8 else 0)
            self._mux[self._s2] = (1 if a & 4 else 0)
            self._mux[self._s1] = (1 if a & 2 else 0)
            self._mux[self._s0] = (1 if a & 1 else 0)
            self._mux.write()
        else:
            if self.__size == 16:
                self._s3.value(1 if a & 8 else 0)
            self._s2.value(1 if a & 4 else 0)
            self._s1.value(1 if a & 2 else 0)
            self._s0.value(1 if a & 1 else 0)
        if return_voltage is True or return_voltage is None and self._return_voltages is True:
            return self._adc.readVoltage()
        else:
            return self._adc.readRaw()

    def readVoltage(self, a):
        return self.read(a, return_voltage=True)

    def readRaw(self, a):
        return self.read(a, return_voltage=False)

    def ADC(self, i, *args, **kwargs):
        """ compatible to machine.ADC, returns an ADC object"""
        return ADC(self, i)

    def atten(self, *args, **kwargs):
        self._adc.atten(*args, **kwargs)

    def width(self, *args, **kwargs):
        self._adc.width(*args, **kwargs)


class ADC(_pyADC):
    def __init__(self, amux: Amux, pin):
        super().__init__()
        self.__amux = amux
        self.__pin = pin

    def read(self):
        return self.__amux.read(self.__pin)

    def readVoltage(self):
        return self.__amux.readVoltage(self.__pin)

    def readRaw(self):
        return self.__amux.readRaw(self.__pin)

    def __str__(self):
        return "amuxADC({!s})".format(self.__pin)

    # Careful using the methods below as they change values for all readings of the Amux

    def atten(self, *args, **kwargs):
        self.__amux.atten(*args, **kwargs)

    def width(self, *args, **kwargs):
        self.__amux.width(*args, **kwargs)
