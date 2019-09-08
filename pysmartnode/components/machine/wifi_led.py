# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-07

"""
Does not provide discovery as no sensor or switch, just a state/activity output of wifi status.
Best to be activated in config.py so it can display the status before receving/loading any additional config.
Therefore no example configuration given.
"""

__updated__ = "2019-09-08"
__version__ = "0.2"

import gc
import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.component import Component
import network
import uasyncio as asyncio
import time

gc.collect()


class WIFILED(Component):
    def __init__(self, pin, active_high=True):
        super().__init__()
        self.pin = Pin(pin, machine.Pin.OUT, value=0 if active_high else 1)
        self._active_high = active_high

    async def _init(self):
        # await super()._init()  # not needed as no mqtt subscription or discovery and could block if no network
        sta = network.WLAN(network.STA_IF)
        while sta.isconnected() is True:
            await self.async_flash(20)
            st = time.ticks_ms()
            while time.ticks_ms() - st < 60000:
                await asyncio.sleep(1)
        while sta.isconnected() is False:
            for _ in range(3):
                await self.async_flash(500)
                await asyncio.sleep(0.5)
            await asyncio.sleep(5)

    def flash(self, duration):
        self.pin.value(1 if self._active_high else 0)
        time.sleep_ms(duration)
        self.pin.value(0 if self._active_high else 1)

    async def async_flash(self, duration):
        self.pin.value(1 if self._active_high else 0)
        await asyncio.sleep_ms(duration)
        self.pin.value(0 if self._active_high else 1)
