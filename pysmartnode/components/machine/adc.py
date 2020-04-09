# Author: Kevin Köck
# Copyright Kevin Köck 2018-2020 Released under the MIT license
# Created on 2018-07-16

"""
example config:
{
    package: .machine.adc
    component: ADC
    constructor_args: {
        pin: 0              # ADC pin number or ADC object (even Amux pin object)
        # calibration_v_max: 3.3   # optional, v_max for calibration of bad ADC sensors. defaults to 3.3V
        # calibration_offset: 0   # optional, voltage offset for calibration of bad ADC sensors
        # atten: null          # optional, attn value to use. Voltages aren't adapted to this config, set the calibration kwargs for it to work
        # max_voltage: null      # optional, defaults to calibration_v_max+calibration_offset
    }
}
Does not publish anything, just unifies reading of esp8266 ADC, esp32, Amux, Arudino, etc
You can pass any ADC object or pin number to ADC() and it will return a corretly subclassed pyADC object
"""

__version__ = "1.7"
__updated__ = "2020-04-09"

import machine
from sys import platform


class pyADC:
    """
    Just a base class to identify all instances of an ADC object sharing the same API
    """

    def __init__(self, *args, calibration_v_max=3.3, calibration_offset=0, max_voltage=None,
                 **kwargs):
        self._cvm = calibration_v_max
        self._co = calibration_offset
        self._mv = max_voltage or calibration_v_max + calibration_offset

    def convertToVoltage(self, raw):
        if platform == "esp8266":
            v = raw / 1023 * self._cvm + self._co
        elif platform == "esp32":
            v = raw / 4095 * self._cvm + self._co
        else:
            v = raw / 65535 * self._cvm + self._co  # every platform now provides this method
        if v > self._mv:
            return self._mv
        elif v < 0:
            return 0.0
        else:
            return v

    def readVoltage(self) -> float:
        """
        Return voltage according to used platform. Atten values are not recognized
        :return: float
        """
        if platform in ("esp8266", "esp32"):
            raw = self.read()
        else:
            try:
                raw = self.read_u16()  # every platform should now provide this method
            except NotImplementedError:
                raise NotImplementedError(
                    "Platform {!s} not implemented, please report".format(platform))
        return self.convertToVoltage(raw)

    def __str__(self):
        return "pyADC generic instance"

    __repr__ = __str__

    def maxVoltage(self) -> float:
        return self._mv

    # When using the machineADC class, the following methods are overwritten by machine.ADC,
    # the machine methods of the hardware ADC.
    # In other subclasses they have to be implemented.

    def read(self) -> int:
        raise NotImplementedError("Implement your subclass correctly!")

    def read_u16(self) -> int:
        """returns 0-65535"""
        raise NotImplementedError("Implement your subclass correctly!")

    def atten(self, *args, **kwargs):
        raise NotImplementedError("Atten not supported")

    def width(self, *args, **kwargs):
        raise NotImplementedError("Width not supported")


# machineADC = type("ADC", (machine.ADC, pyADC), {})  # machine.ADC subclass
class machineADC(machine.ADC, pyADC):
    # machine.Pin ignores additional kwargs in constructor
    pass


def ADC(pin, *args, atten=None, calibration_v_max=3.3, calibration_offset=0, max_voltage=3.3,
        **kwargs) -> pyADC:
    if type(pin) == str:
        raise TypeError("ADC pin can't be string")
    if isinstance(pin, pyADC):
        # must be a completely initialized ADC otherwise it wouldn't be a subclass of pyADC
        # could be machineADC, Arduino ADC or even Amux or Amux ADC object
        return pin
    if type(pin) == machine.ADC:
        # using a hacky way to re-instantiate an object derived from machine.ADC by
        # reading the used pin from machine.ADC string representation and creating it again.
        # This does not retain the set atten value sadly.
        # It is however needed so that isinstance(adc, machine.ADC) is always True for hardware ADCs.
        astr = str(pin)
        if platform == "esp8266":  # esp8266 only has one ADC
            pin = 0
        elif platform == "esp32":  # ADC(Pin(33))
            pin = int(astr[astr.rfind("(") + 1:astr.rfind("))")])
        else:
            try:
                pin = int(astr[astr.rfind("(") + 1:astr.rfind("))")])
            except Exception as e:
                raise NotImplementedError(
                    "Platform {!s} not implemented, str {!s}, {!s}".format(platform, astr, e))
    if type(pin) == int:
        if platform == "esp32":
            adc = machineADC(machine.Pin(pin), *args, calibration_v_max=calibration_v_max,
                             calibration_offset=calibration_offset, max_voltage=max_voltage,
                             **kwargs)
            adc.atten(adc.ATTN_11DB if atten is None else atten)
            return adc
        elif platform == "esp8266":
            return machineADC(pin, *args, calibration_v_max=calibration_v_max,
                              calibration_offset=calibration_offset, max_voltage=max_voltage,
                              **kwargs)  # esp8266 does not require a pin object
        else:
            try:
                return machineADC(machine.Pin(pin), *args, calibration_v_max=calibration_v_max,
                                  calibration_offset=calibration_offset, max_voltage=max_voltage,
                                  **kwargs)
            except Exception as e:
                raise NotImplementedError(
                    "Platform {!s} not implemented, please report. Fallback resulted in {!s}".format(
                        platform, e))
    raise TypeError("Unknown type {!s} for ADC object".format(type(pin)))
