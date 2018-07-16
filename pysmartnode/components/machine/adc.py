'''
Created on 2018-07-16

@author: Kevin Köck
'''

"""
example config:
{
    package: .machine.adc
    component: ADC
    constructor_args: {
        pin: 0              # ADC pin number or ADC object (even Amux pin object)     
    }
}
Does not publish or read anything, just unifies reading of esp8266 ADC, esp32 loboris fork and Amux
"""

__version__ = "0.1"
__updated__ = "2018-07-16"

import machine
from sys import platform


class ADC:
    def __init__(self, pin):
        if type(pin) == str:
            raise TypeError("ADC pin can't be string")
        self._adc = pin if type(pin) != int else machine.ADC(pin)
        if type(self._adc) == machine.ADC:
            if platform == "esp8266":
                def read_voltage():
                    return self._adc.read() / 1023 * 3.3

                self._read_voltage = read_voltage
            elif platform == "esp32_LoBo":
                self._adc.atten(self._adc.ATTN_11DB)

                def read_voltage():
                    return self._adc.read() / 1000

                self._read_voltage = read_voltage
                self._read_raw = self._adc.readraw
            else:
                raise NotImplementedError("Platform {!s} not implemented, please report".format(platform))
        else:
            # AMUX
            self._read_voltage = self._adc.readVoltage
            self._read_raw = self._adc.readRaw

    def readVoltage(self):
        return self._read_voltage()

    def readRaw(self):
        return self._read_raw()

    def read(self):
        # should not be used as output varies between platforms
        return self._adc.read()

    def readraw(self):
        """ for name compability to loboris fork adc object"""
        return self._read_raw()
