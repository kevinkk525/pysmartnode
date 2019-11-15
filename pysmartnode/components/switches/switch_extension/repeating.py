# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-28

__updated__ = "2019-11-15"
__version__ = "0.4"

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
        _name = component._name if hasattr(component, "_name") else "{!s}{!s}".format(
            COMPONENT_NAME, count)
        topic = _mqtt.getDeviceTopic("{!s}/repeating/on_time".format(_name), is_request=True)
        _mqtt.subscribeSync(topic, self._changeOnTime, extended_switch, check_retained_state=True)
        topic2 = _mqtt.getDeviceTopic("{!s}/repeating/off_time".format(_name), is_request=True)
        _mqtt.subscribeSync(topic2, self._changeOffTime, extended_switch,
                            check_retained_state=True)
        self._task = None

    async def _changeOnTime(self, topic, msg, retain):
        self._on_time = int(msg)
        return True

    async def _changeOffTime(self, topic, msg, retain):
        self._off_time = int(msg)
        return True

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
            self._task = None
            print("repeating exited")

    async def activate(self, extended_switch, component, component_on, component_off):
        """Triggered whenever the mode changes and this mode has been activated"""
        if self._task is not None:
            print("Task already active")
            self._task.cancel()
        self._task = asyncio.create_task(self._repeating(component_on, component_off))
        return True

    async def deactivate(self, extended_switch, component, component_on, component_off):
        """Triggered whenever the mode changes and this mode has been deactivated"""
        self._task.cancel()
        return True

    def __str__(self):
        """Name of the mode, has to be the same as the classname/module"""
        return "repeating"
