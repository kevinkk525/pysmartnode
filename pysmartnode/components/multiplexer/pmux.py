'''
Created on 09.08.2017

@author: Kevin Köck
'''
"""
example config:
{
    package: .multiplexer.pmux, #analog passthrough multiplexer
    component: Pmux
    constructor_args: {
        s0: D5         # muxPin object can be used if a pmux is connected to a mux, then mux can be None
        s1: D2         # if all pins are connected to a mux then pin number can be used and mux object has to be given
        s2: D4  
        #s3: null      #optional, if not given a 8-bit analog multiplexer is used
        mux: null      #optional, if defined then all pins are interpreted as mux pins and have to be integer
        pin: 0          # pin number, can be a pmux pin object (multiple amux) but this will slow down pin changes
        pin_direction: OUT  # optional, defaults to OUT, string of the pin direction as integer is different on platform implementations
        pin_pullup: null    # optional, defaults to None, string of the pin pull 
    }
}
This library uses an analog multiplexer as a pin extender so that each pin can be used for 1-wire, dht, ...
If timings are a problem, use the Pmux.pin object directly, which is a normal Pin object and use Pmux to select the amux pin

"""

__updated__ = "2018-06-20"
__version__ = "2.0"

# Version 2.0 should support an pmux connected to an pmux, not tested though, only have one amux

import machine
from pysmartnode import config
import gc

gc.collect()


class Pmux:
    def __init__(self, s0, s1, s2, pin, s3=None, mux=None, pin_direction="OUT", pin_pull=None):
        """ It is possibile to initialize with:
            - pin numbers (or string on esp8266)
            - mux object and pin numbers (of mux pins)
            - Pin objects (either from machine or mux Pin objects [no mux object needed])
            :type mux: Mux object if a multiplexer is used
            :type pin: pin number or string (esp8266)
            :type pin_direction: str of pin_direction
            s3 is optional, only needed if 16 pins are used, 8 pins possible with s0-s2.
            pmux can be read like a list: value=amux[2]
            pmux can be set like a list: amux[2]=1
        """
        if mux:
            self.s0 = s0
            self.s1 = s1
            self.s2 = s2
            self.s3 = s3
            self.mux = mux
        else:
            if type(s0) == int:
                self.s0 = machine.Pin(s0 if type(s0) != str else config.pins[s0], machine.Pin.OUT)
                self.s1 = machine.Pin(s1 if type(s1) != str else config.pins[s1], machine.Pin.OUT)
                self.s2 = machine.Pin(s2 if type(s2) != str else config.pins[s2], machine.Pin.OUT)
                if s3:
                    self.s3 = machine.Pin(s3 if type(s3) != str else config.pins[s3], machine.Pin.OUT)
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
        self._selected_pin = None
        if pin_direction not in dir(machine.Pin):
            raise TypeError("Pin_direction {!r} does not exist".format(pin_direction))
        self.pin = machine.Pin(pin if type(pin) != str else config.pins[pin],
                               getattr(machine.Pin, pin_direction), pin_pull)

    def __getitem__(self, a):
        return self.value(a)

    def __setitem__(self, a, direction):
        return self.value(a, direction)

    def getSize(self):
        """ Get number of pins"""
        return self.__size

    def _selectPin(self, a):
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

    def value(self, a, value=None):
        if a != self._selected_pin:
            # only select pin if needed as it would slow IO-operations down and screw timings
            self._selectPin(a)
        if value is None:
            return self.pin.value()
        else:
            return self.pin.value(value)

    def mode(self, mode):
        if type(mode) == str:
            if mode not in dir(machine.Pin):
                raise TypeError("Mode {!r} is not available".format(mode))
            mode = getattr(machine.Pin, mode)
        self.pin.mode(mode)

    def pull(self, p=None):
        return self.pin.pull(p)

    def drive(self, d=None):
        return self.pin.drive(d)

    def init(self, *args, **kwargs):
        self.pin.init(*args, **kwargs)

    def Pin(self, p):
        return Pin(self, p)


class Pin:
    def __init__(self, pmux, pin):
        self.__pmux = pmux
        self.__pin = pin

    def value(self, value=None):
        return self.__pmux.value(self.__pin, value)

    def mode(self, m):
        self.__pmux.mode(m)

    def on(self):
        self.__pmux.value(self.__pin, 1)

    def off(self):
        self.__pmux.value(self.__pin, 0)

    def pull(self, p=None):
        # only if pin supports function
        return self.__pmux.pin.pull(p)

    def drive(self, d=None):
        # only if pin supports function
        return self.__pmux.pin.drive(d)

    def init(self, *args, **kwargs):
        self.__pmux.pin.init(*args, **kwargs)

    def __call__(self, x=None):
        return self.value(x)

    def __str__(self):
        return "pmuxPin({!s})".format(self.__pin)
