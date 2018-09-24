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
    }
}
"""

__updated__ = "2018-08-31"
__version__ = "0.2"

import gc
import uasyncio as asyncio
import machine
from pysmartnode.utils import sys_vars

gc.collect()
from pysmartnode import logging


class WDT:
    def __init__(self, id=0, timeout=120):
        self._timeout = timeout / 10
        self._counter = 0
        self._timer = machine.Timer(id)
        self.init()
        asyncio.get_event_loop().create_task(self._resetCounter())
        if sys_vars.hasFilesystem():
            try:
                with open("watchdog.txt", "r") as f:
                    if f.read() == "True":
                        log.warn("Reset reason: Watchdog")
            except Exception as e:
                print(e)  # file probably just does not exist
            try:
                with open("watchdog.txt", "w") as f:
                    f.write("False")
            except Exception as e:
                logging.getLogger("WDT").error("Error saving to file: {!s}".format(e))

    def _wdt(self, t):
        self._counter += self._timeout
        if self._counter >= self._timeout * 10:
            if sys_vars.hasFilesystem():
                try:
                    with open("watchdog.txt", "w") as f:
                        f.write("True")
                except Exception as e:
                    print("Error saving to file: {!s}".format(e))
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
