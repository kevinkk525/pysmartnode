# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-07

"""
Does not provide discovery as no sensor or switch, just a state/activity output of wifi status.
Best to be activated in config.py so it can display the status before receving/loading any additional config.
Therefore no example configuration given.
"""

__updated__ = "2019-11-02"
__version__ = "1.4"

import gc
import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.component import Component
import network
import uasyncio as asyncio
import time
from pysmartnode import config

gc.collect()

COMPONENT_NAME = "WifiLED"


class WIFILED(Component):
    def __init__(self, pin, active_high=True):
        super().__init__(COMPONENT_NAME, __version__, discover=False, unit_index=0)
        self.pin = Pin(pin, machine.Pin.OUT, value=0 if active_high else 1)
        self._active_high = active_high
        self._next = []
        asyncio.get_event_loop().create_task(self._loop())

    async def _loop(self):
        mqtt = config.getMQTT()
        mqtt.registerWifiCallback(self._wifiChanged)
        mqtt.registerConnectedCallback(self._reconnected)
        await self._flash(500, 1)
        sta = network.WLAN(network.STA_IF)
        st = time.ticks_ms()
        while True:
            while self._next:
                await self._flash(*self._next.pop(0))
                await asyncio.sleep(1)
            if time.ticks_diff(time.ticks_ms(), st) > 60000:  # heartbeat
                st = time.ticks_ms()
                if sta.isconnected():
                    await self._flash(20, 1)
                    await asyncio.sleep_ms(250)
                    await self._flash(20, 1)
                else:
                    await self._flash(500, 3)
            await asyncio.sleep_ms(500)

    async def _flash(self, duration, iters):
        for _ in range(iters):
            self.pin.value(1 if self._active_high else 0)
            await asyncio.sleep_ms(duration)
            self.pin.value(0 if self._active_high else 1)
            await asyncio.sleep_ms(duration)

    async def _wifiChanged(self, state):
        if state is True:
            self._next.append((50, 2))
        else:
            self._next.append((500, 3))

    async def _reconnected(self, client):
        self._next.append((100, 5))
