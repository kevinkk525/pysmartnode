'''
Created on 09.08.2017

@author: Kevin Köck
'''

"""
example config:
{
    package: .multiplexer.mux,
    component: Mux,
    constructor_args: {
        shift_pin: D5
        store_pin: D2   
        data_pin: D4
        #number_multiplexer: 2                #optional, defaults to 1, no limit
    }
}
"""

__updated__ = "2018-08-18"
__version__ = "0.7"

import machine
from pysmartnode.components.machine.pin import Pin as PyPin
import gc

gc.collect()


class Mux:
    def __init__(self, shift_pin, store_pin, data_pin, number_multiplexer=1):
        self.shcp = PyPin(shift_pin, machine.Pin.OUT)
        self.stcp = PyPin(store_pin, machine.Pin.OUT)
        self.ds = PyPin(data_pin, machine.Pin.OUT)
        self.__data = bytearray()
        for i in range(0, 8 * number_multiplexer):
            self.__data.append(0)
        self.__size = number_multiplexer
        self.write()

    def write(self):
        self.stcp.value(0)
        for i in range((8 * self.__size) - 1, -1, -1):
            self.shcp.value(0)
            self.ds.value(self.__data[i])
            self.shcp.value(1)
        self.stcp.value(1)

    def __setitem__(self, a, b):
        if b != 1 and b != 0:
            raise ValueError("Value must be 1 or 0")
        self.__data[a] = b

    def __getitem__(self, a):
        return self.__data[a]

    def __delitem__(self, a):
        self.__data[a] = 0

    def set(self, i):
        self.__data[i] = 1

    def clear(self, i):
        self.__data[i] = 0

    def getSize(self):
        """ Get number of pins"""
        return self.__size * 8

    def Pin(self, i, *args, **kwargs):
        return Pin(self, i)


class Pin:
    def __init__(self, mux, pin):
        self.__mux = mux
        self.__pin = pin

    def value(self, inp=None, wait=False):
        if inp is not None:
            if inp == 1:
                self.__mux.set(self.__pin)
                if not wait:
                    self.__mux.write()
            elif inp > 1:
                raise ValueError("Value must be 1 or 0")
            else:
                self.__mux.clear(self.__pin)
                if not wait:
                    self.__mux.write()
        else:
            return self.__mux[self.__pin]

    def __str__(self):
        return "muxPin({!s})".format(self.__pin)

    def on(self):
        self.__mux.value(self.__pin, 1)

    def off(self):
        self.__mux.value(self.__pin, 0)

    def __call__(self, x=None):
        return self.value(x)
