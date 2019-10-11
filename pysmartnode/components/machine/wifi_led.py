# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-07

"""
Does not provide discovery as no sensor or switch, just a state/activity output of wifi status.
Best to be activated in config.py so it can display the status before receving/loading any additional config.
Therefore no example configuration given.
"""

__updated__ = "2019-09-29"
__version__ = "1.2"

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
        super().__init__(COMPONENT_NAME, __version__)
        self.pin = Pin(pin, machine.Pin.OUT, value=0 if active_high else 1)
        self._active_high = active_high
        self.lock = config.Lock()
        asyncio.get_event_loop().create_task(self._loop())
        # discovery although not used could block if no network,
        # mqtt not needed but will log that this component is used

    async def _init_network(self):
        await super()._init_network()

    async def _loop(self):
        mqtt = config.getMQTT()
        mqtt.registerWifiCallback(self._wifiChanged)
        mqtt.registerConnectedCallback(self._reconnected)
        await self.async_flash(500, 1)
        await asyncio.sleep(2)
        sta = network.WLAN(network.STA_IF)
        while True:
            while sta.isconnected() is True:
                await self.async_flash(20, 1)
                st = time.ticks_ms()
                while time.ticks_diff(time.ticks_ms(), st) < 30000:
                    await asyncio.sleep(1)
            await asyncio.sleep(5)
            # to let wifi subscription blink first and wifi reconnect if it was just a brief outage
            while sta.isconnected() is False:
                await self.async_flash(500, 3)
                await asyncio.sleep(5)

    def flash(self, duration, iters):
        for _ in range(iters):
            self.pin.value(1 if self._active_high else 0)
            time.sleep_ms(duration)
            self.pin.value(0 if self._active_high else 1)
            time.sleep_ms(duration)

    async def async_flash(self, duration, iters):
        async with self.lock:
            for _ in range(iters):
                self.pin.value(1 if self._active_high else 0)
                await asyncio.sleep_ms(duration)
                self.pin.value(0 if self._active_high else 1)
                await asyncio.sleep_ms(duration)

    async def _wifiChanged(self, state):
        if state is True:
            await self.async_flash(50, 5)
        else:
            await self.async_flash(500, 5)

    async def _reconnected(self, client):
        await self.async_flash(300, 2)
