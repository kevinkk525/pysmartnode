# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2021-05-25

__updated__ = "2021-05-27"
__version__ = "0.3"

import errno
import uasyncio as asyncio
import time
import machine
import sys
from pysmartnode.components.machine.adc import pyADC as _pyADC

# timestamp in readings currently unused


class ArduinoSensors:
    def __init__(self, uart, vcc=5, adc_read_interval=50):
        self._uart: machine.UART = uart
        self._suart = asyncio.StreamReader(uart)
        self._lock = asyncio.Lock()
        self._vcc = vcc
        self._res = {}
        self._adc_task = None
        self._adc_read_int = adc_read_interval

    async def _adc_read(self):
        while True:
            try:
                res = await self.read("adc", int, timeout=1000)
            except Exception as e:
                print("adc",e)
            else:
                self._add_result("adc", res)
            await asyncio.sleep_ms(self._adc_read_int)

    def _add_result(self, name, value):
        if name not in self._res:
            ev = asyncio.Event()
            self._res[name] = (None, time.ticks_ms(), ev)
        ev = self._res[name][2]
        ev.set()
        self._res[name] = (value, time.ticks_ms(), ev)

    async def _watch(self):
        pass

    def read_sync(self, name, return_type=None):
        if name not in self._res or self._res[name][0] is None:
            raise AttributeError("{} does not exist".format(name))
        res = self._res[name][0]
        if type(res) not in (tuple, list):
            return res if not return_type else return_type(res)
        if return_type:
            return [return_type(res[i]) for i in range(1, len(res))]
        else:
            return res[1:]

    def time_sync(self, name):
        if name not in self._res:
            raise AttributeError("{} does not exist".format(name))
        return self._res[name][1]

    async def await_read(self, name, return_type=None):
        if name not in self._res:
            ev = asyncio.Event()
            self._res[name] = (None, time.ticks_ms(), ev)
        else:
            ev=self._res[name][2]
        await ev.wait()
        ev.clear()
        return self.read_sync(name, return_type)

    def _process_read(self,res,name,return_type):
        if res:
            try:
                res = res.decode().rstrip("\r\n").split(";")
                if res[0] != name:
                    print("Excepted result name {} but got {}".format(name, res[0]))
                    raise AttributeError("unexpected name")
                if len(res) == 2:
                    return return_type(res[1])
                else:
                    if return_type:
                        return [return_type(res[i]) for i in range(1, len(res))]
                    else:
                        return res[1:]
            except AttributeError:
                raise
            except Exception as e:
                sys.print_exception(e)
                raise OSError(errno.EBADF)

    async def _read(self, name, return_type=None):
        async with self._lock:
            self._uart.write(name+"\n")
            while True:
                res = await self._suart.readline()
                try:
                    return self._process_read(res,name,return_type)
                except AttributeError:
                    print("Caught Attribute error")
                    pass # got wrong value. Can happen due to a timeout

    async def read(self, name, return_type=None, timeout=1000):
        try:
            return await asyncio.wait_for_ms(self._read(name, return_type), timeout)
        except asyncio.TimeoutError:
            raise OSError(errno.ETIMEDOUT)

    def getVoltage(self):
        return self._vcc


class ADC(_pyADC):
    def __init__(self, arduino:ArduinoSensors, pin):
        super().__init__(calibration_v_max=arduino.getVoltage())
        if pin not in ("A2","A3","A5"):
            raise TypeError("Pin {} not available".format(pin))
        self._pin=pin
        self._ard=arduino
        if self._ard._adc_task is None:
            self._ard._adc_task = asyncio.create_task(self._ard._adc_read())
            self._ard._add_result("adc",None)

    def read_u16(self):
        res=self._ard.read_sync("adc",int)
        if res is None:
            return 0
        for i,a in enumerate(("A2","A3","A5")):
            if self._pin == a:
                if time.ticks_diff(time.ticks_ms(),self._ard.time_sync("adc"))>2.1*self._ard._adc_read_int:
                    return 0 # default value if connection problem
                return res[i]/1023*65535
