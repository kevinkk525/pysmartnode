'''
Created on 29.05.2018

@author: Kevin Köck
'''

"""
example config:
{
    package: .machine.watchdog
    component: WDT
    constructor_args: {
        id: 0                   #optional, number of the timer to be used
        timeout: 120            #optional, defaults to 120s, resets machine after this
        # use_rtc_memory: true  #optional, use rtc memory as backup if filesystem not available, only esp8266 supported
    }
}
"""

__updated__ = "2018-10-19"
__version__ = "1.1"

import gc
import uasyncio as asyncio
import machine
from pysmartnode.utils import sys_vars
from sys import platform

gc.collect()
from pysmartnode import logging


class WDT:
    def __init__(self, id=0, timeout=120, use_rtc_memory=True):
        self._timeout = timeout / 10
        self._counter = 0
        self._timer = machine.Timer(id)
        self._use_rtc_memory = use_rtc_memory
        self._has_filesystem = False
        self.init()
        asyncio.get_event_loop().create_task(self._resetCounter())
        if sys_vars.hasFilesystem():
            self._has_filesystem = True
            try:
                with open("watchdog.txt", "r") as f:
                    if f.read() == "True":
                        logging.getLogger("WDT").warn("Reset reason: Watchdog")
            except Exception as e:
                print(e)  # file probably just does not exist
            try:
                with open("watchdog.txt", "w") as f:
                    f.write("False")
            except Exception as e:
                logging.getLogger("WDT").error("Error saving to file: {!s}".format(e))
        elif use_rtc_memory and platform == "esp8266":
            rtc = machine.RTC()
            if rtc.memory() == b"WDT reset":
                logging.getLogger("WDT").critical("Reset reason: Watchdog")
            rtc.memory(b"")

    def _wdt(self, t):
        self._counter += self._timeout
        if self._counter >= self._timeout * 10:
            if self._has_filesystem:
                try:
                    with open("watchdog.txt", "w") as f:
                        f.write("True")
                except Exception as e:
                    print("Error saving to file: {!s}".format(e))
            elif self._use_rtc_memory and platform == "esp8266":
                rtc = machine.RTC()
                rtc.memory(b"WDT reset")
            machine.reset()

    def feed(self):
        self._counter = 0

    def init(self, timeout=None):
        timeout = timeout or self._timeout
        self._timeout = timeout
        self._timer.init(period=int(self._timeout * 1000), mode=machine.Timer.PERIODIC, callback=self._wdt)

    def deinit(self):  # will not stop coroutine
        self._timer.deinit()

    async def _resetCounter(self):
        while True:
            await asyncio.sleep(self._timeout)
            self.feed()
