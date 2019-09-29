# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-28

__updated__ = "2019-09-28"
__version__ = "0.1"

from pysmartnode.components.switches.switch_extension import Switch, ComponentSwitch, _mqtt, \
    COMPONENT_NAME, BaseMode
import uasyncio as asyncio
import time


class repeating(BaseMode):
    """
    Shut down device after configured amount of time
    """

    def __init__(self, extended_switch: Switch, component: ComponentSwitch, component_on,
                 component_off):
        self._on_time = 30  # default value to be adapted by mqtt
        self._off_time = 30  # default value to be adapted by mqtt
        count = component._count if hasattr(component, "_count") else ""
        topic = _mqtt.getDeviceTopic("{!s}{!s}/repeating/on_time".format(COMPONENT_NAME, count),
                                     is_request=True)
        extended_switch._subscribe(topic, self._changeOnTime)
        topic2 = _mqtt.getDeviceTopic("{!s}{!s}/repeating/off_time".format(COMPONENT_NAME, count),
                                      is_request=True)
        extended_switch._subscribe(topic, self._changeOffTime)
        self._coro = None
        asyncio.get_event_loop().create_task(self._init(topic, topic2))

    async def _init(self, topic, topic2):
        await _mqtt.subscribe(topic, qos=1, await_connection=False)
        await _mqtt.subscribe(topic2, qos=1, await_connection=False)

    async def _changeOnTime(self, topic, msg, retain):
        self._on_time = int(msg)

    async def _changeOffTime(self, topic, msg, retain):
        self._off_time = int(msg)

    async def _repeating(self, component_on, component_off):
        print("repeating started")
        try:
            while True:
                st = time.ticks_ms()
                await component_on()
                while time.ticks_diff(time.ticks_ms(), st) < self._on_time * 1000:
                    await asyncio.sleep(0.2)
                await component_off()
                st = time.ticks_ms()
                while time.ticks_diff(time.ticks_ms(), st) < self._off_time * 1000:
                    await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            print("repeating canceled")
        finally:
            await component_off()
            self._coro = None
            print("repeating exited")

    async def activate(self, extended_switch, component, component_on, component_off):
        """Triggered whenever the mode changes and this mode has been activated"""
        if self._coro is not None:
            print("Coro already active")
            asyncio.cancel(self._coro)
        self._coro = self._repeating(component_on, component_off)
        asyncio.get_event_loop().create_task(self._coro)
        return True

    async def deactivate(self, extended_switch, component, component_on, component_off):
        """Triggered whenever the mode changes and this mode has been deactivated"""
        asyncio.cancel(self._coro)
        return True

    def __str__(self):
        """Name of the mode, has to be the same as the classname/module"""
        return "repeating"
