# Author: Kevin Köck
# Copyright Kevin Köck 2018-2020 Released under the MIT license
# Created on 2018-05-29

"""
example config:
{
    package: .machine.watchdog
    component: WDT
    constructor_args: {
        id: 0                   #optional, number of the timer to be used
        timeout: 120            #optional, defaults to 120s, resets machine after this
        hard: false             # optional, hard=True is hardware WDT (if available)
    }
}
Warning: A hardware WDT doesn't log the reset.
"""

__updated__ = "2021-05-31"
__version__ = "1.4"

import gc
import uasyncio as asyncio
import machine
from sys import platform

gc.collect()


class WDT:
    def __init__(self, id=0, timeout=120, hard=False):
        self._timeout = timeout / 10
        if not hard:
            self._counter = 0
            self._timer = machine.Timer(id)
            self.init()
        else:
            self._wdt = machine.WDT(id, timeout=timeout*1000)
        self._hard = hard
        asyncio.create_task(self._resetCounter())
        """ Done in pysmartnode.main
        try:
            with open("reset_reason.txt", "r") as f:
                if f.read() == "True":
                    logging.getLogger("WDT").warn("Reset reason: Watchdog")
        except Exception as e:
            print(e)  # file probably just does not exist
        try:
            os.remove("reset_reason.txt")
        except Exception as e:
            logging.getLogger("WDT").error("Error saving to file: {!s}".format(e))
        """

    def _wdt(self, t):
        self._counter += self._timeout
        if self._counter >= self._timeout * 10:
            try:
                with open("reset_reason.txt", "w") as f:
                    f.write("WDT reset")
            except Exception as e:
                print("Error saving to file: {!s}".format(e))
            machine.reset()

    def feed(self):
        self._counter = 0

    def init(self, timeout=None):
        timeout = timeout or self._timeout
        self._timeout = timeout / 10
        self._timer.init(period=int(self._timeout * 1000), mode=machine.Timer.PERIODIC,
                         callback=self._wdt)

    def deinit(self):  # will not stop coroutine
        if self._hard:
            raise AttributeError("Hardware WDT can't be deinitialized")
        self._timer.deinit()

    async def _resetCounter(self):
        while True:
            await asyncio.sleep(self._timeout)
            if self._hard:
                self._wdt.feed()
            else:
                self.feed()
