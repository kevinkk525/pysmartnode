# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-10 

__updated__ = "2019-10-20"
__version__ = "0.7"

from pysmartnode.utils.component import Component
from .definitions import DISCOVERY_SWITCH
from pysmartnode import config
import gc
from micropython import const

_mqtt = config.getMQTT()
_TIMEOUT = const(10)  # wait for a single reconnect but should be short enough if not connected


class ComponentSwitch(Component):
    """
    Generic Switch class.
    Use it according to the template.
    """

    def __init__(self, component_name, version, command_topic=None, instance_name=None,
                 wait_for_lock=True, discover=True, restore_state=True):
        """
        :param component_name: name of the component that is subclassing this switch (used for discovery and topics)
        :param version: version of the component module. will be logged over mqtt
        :param command_topic: command_topic of subclass which controls the switch state. optional.
        :param instance_name: name of the instance. If not provided will get composed of component_name<count>
        :param wait_for_lock: if True then every request waits for the lock to become available,
        :param restore_state: restore the retained state topic state
        meaning the previous device request has to finish before the new one is started.
        Otherwise the new one will get ignored.
        """
        super().__init__(component_name, version, discover=discover)
        # discover: boolean, if this component should publish its mqtt discovery.
        # This can be used to prevent combined Components from exposing underlying
        # hardware components like a power switch

        self._state = None  # initial state is unknown
        self._topic = command_topic or _mqtt.getDeviceTopic(
            "{!s}{!s}/set".format(component_name, self._count))
        _mqtt.subscribe(self._topic, self.on_message, self, check_retained_state=restore_state)
        self.lock = config.Lock()
        # in case switch activates a device that will need a while to finish
        self._wfl = wait_for_lock
        self._name = instance_name
        self._count = ""  # declare in subclass
        gc.collect()

    async def on_message(self, topic, msg, retain):
        """
        Standard callback to change the device state from mqtt.
        Can be subclassed if extended functionality is needed.
        """
        if msg in _mqtt.payload_on:
            if not self._state:  # False or None (unknown)
                await self.on()
        elif msg in _mqtt.payload_off:
            if self._state is not False:  # True or None (unknown)
                await self.off()
        else:
            raise TypeError("Payload {!s} not supported".format(msg))
        return False  # will not publish the requested state to mqtt as already done by on()/off()

    async def on(self):
        """Turn switch on. Can be used by other components to control this component"""
        if self.lock.locked() is True and self._wfl is False:
            return False
        async with self.lock:
            res = await self._on()  # if _on() returns True the value should be published
            if res is True:
                self._state = True
                await _mqtt.publish(self._topic[:-4], "ON", qos=1, retain=True, timeout=_TIMEOUT)
            return res

    async def off(self):
        """Turn switch off. Can be used by other components to control this component"""
        if self.lock.locked() is True and self._wfl is False:
            return False
        async with self.lock:
            res = await self._off()  # if _off() returns True the value should be published
            if res is True:
                self._state = False
                await _mqtt.publish(self._topic[:-4], "OFF", qos=1, retain=True, timeout=_TIMEOUT)
            return res

    async def toggle(self):
        """Toggle device state. Can be used by other component to control this component"""
        if self._state is True:
            return await self.off()
        else:
            return await self.on()

    def state(self):
        return self._state

    async def _discovery(self):
        name = self._name or "{!s}{!s}".format(self.COMPONENT_NAME, self._count)
        await self._publishDiscovery("switch", self._topic[:-4], name, DISCOVERY_SWITCH, self._frn)
        # note that _publishDiscovery does expect the state topic
        # but we have the command topic stored.

    def topic(self):
        return self._topic
