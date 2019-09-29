# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-10 

__updated__ = "2019-09-29"
__version__ = "0.4"

from pysmartnode.utils.component import Component
from .definitions import DISCOVERY_SWITCH
from pysmartnode import config
import gc
import uasyncio as asyncio
from micropython import const

_mqtt = config.getMQTT()
_TIMEOUT = const(10)  # wait for a single reconnect but should be short enough if not connected


class ComponentSwitch(Component):
    """
    Generic Switch class.
    Use it according to the template.
    """

    def __init__(self, component_name, version, command_topic=None, instance_name=None,
                 wait_for_lock=True):
        """
        :param component_name: name of the component that is subclassing this switch (used for discovery and topics)
        :param version: version of the component module. will be logged over mqtt
        :param command_topic: command_topic of subclass which controls the switch state. optional.
        :param instance_name: name of the instance. If not provided will get composed of component_name<count>
        :param wait_for_lock: if True then every request waits for the lock to become available,
        meaning the previous device request has to finish before the new one is started.
        Otherwise the new one will get ignored.
        """
        super().__init__(component_name, version)
        self._state = False
        self._topic = command_topic or _mqtt.getDeviceTopic(
            "{!s}{!s}".format(component_name, self._count),
            is_request=True)
        self.lock = config.Lock()
        # in case switch activates a device that will need a while to finish
        self._wfl = wait_for_lock
        self._name = instance_name
        gc.collect()

    async def _init(self):
        t = self._topic[:-4]
        self._subscribe(t, self.on_message)  # get retained state topic
        await super()._init()
        await asyncio.sleep_ms(500)
        await _mqtt.unsubscribe(t, self)
        del t
        self._subscribe(self._topic, self.on_message)
        await _mqtt.subscribe(self._topic)

    async def on_message(self, topic, msg, retain):
        """
        Standard callback to change the device state from mqtt.
        Can be subclassed if extended functionality is needed.
        """
        if memoryview(topic) == memoryview(self._topic)[:-4]:
            if retain:
                await _mqtt.unsubscribe(topic, self, await_connection=False)
            else:
                return False
        if msg in _mqtt.payload_on:
            if self._state is False:
                await self.on()
        elif msg in _mqtt.payload_off:
            if self._state is True:
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
