# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-10 

__updated__ = "2020-03-04"
__version__ = "1.2"

from pysmartnode.utils.component import Component
from .definitions import DISCOVERY_SWITCH
from pysmartnode import config
import gc
from micropython import const
import uasyncio as asyncio

_mqtt = config.getMQTT()


class ComponentSwitch(Component):
    """
    Generic Switch class.
    Use it according to the template.
    """

    def __init__(self, component_name, version, unit_index: int, command_topic=None,
                 instance_name=None, wait_for_lock=True, discover=True, restore_state=True,
                 friendly_name=None, initial_state=None):
        """
        :param component_name: name of the component that is subclassing this switch (used for discovery and topics)
        :param version: version of the component module. will be logged over mqtt
        :param unit_index: counter of the registerd unit of this sensor_type (used for default topics)
        :param command_topic: command_topic of subclass which controls the switch state. optional.
        :param instance_name: name of the instance. If not provided will get composed of component_name<count>
        :param wait_for_lock: if True then every request waits for the lock to become available,
        :param restore_state: restore the retained state topic state
        meaning the previous device request has to finish before the new one is started.
        Otherwise the new one will get ignored.
        :param friendly_name: friendly name for homeassistant gui
        :param initial_state: intitial state of the switch. By default unknown so first state change request will set initial state.
        """
        super().__init__(component_name, version, unit_index, discover=discover)
        # discover: boolean, if this component should publish its mqtt discovery.
        # This can be used to prevent combined Components from exposing underlying
        # hardware components like a power switch

        self._state = initial_state  # initial state is unknown if None
        self._topic = command_topic or _mqtt.getDeviceTopic(
            "{!s}{!s}/set".format(component_name, self._count))
        _mqtt.subscribeSync(self._topic, self.on_message, self, check_retained_state=restore_state)
        self.lock = config.Lock()
        # in case switch activates a device that will need a while to finish
        self._wfl = wait_for_lock
        self._name = instance_name
        self._event = None
        self._frn = friendly_name
        self._pub_task = None
        gc.collect()

    def getStateChangeEvent(self):
        """
        Returns an event that gets triggered on every state change
        :return: Event
        """
        if self._event is None:
            from pysmartnode.utils.event import Event
            self._event = Event()
        return self._event

    def _setState(self, state):
        if state != self._state and self._event is not None:
            self._event.set(state)
        self._state = state

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

    async def __publish(self, msg):
        await _mqtt.publish(self._topic[:-4], msg, qos=1, retain=True)
        self._pub_task = None

    async def on(self):
        """Turn switch on. Can be used by other components to control this component"""
        if self.lock.locked() is True and self._wfl is False:
            return False
        async with self.lock:
            res = await self._on()  # if _on() returns True the value should be published
            if res is True:
                self._setState(True)
                if self._pub_task:
                    asyncio.cancel(self._pub_task)
                    self._pub_task = None
                self._pub_task = asyncio.get_event_loop().create_task(self.__publish("ON"))            
            return res

    async def off(self):
        """Turn switch off. Can be used by other components to control this component"""
        if self.lock.locked() is True and self._wfl is False:
            return False
        async with self.lock:
            res = await self._off()  # if _off() returns True the value should be published
            if res is True:
                self._setState(False)
                if self._pub_task:
                    asyncio.cancel(self._pub_task)
                    self._pub_task = None
                self._pub_task = asyncio.get_event_loop().create_task(self.__publish("OFF"))
            return res

    async def toggle(self):
        """Toggle device state. Can be used by other component to control this component"""
        if self._state is True:
            return await self.off()
        else:
            return await self.on()

    def state(self):
        return self._state

    async def _discovery(self, register=True):
        name = self._name or "{!s}{!s}".format(self.COMPONENT_NAME, self._count)
        if register:
            await self._publishDiscovery("switch", self._topic[:-4], name, DISCOVERY_SWITCH,
                                         self._frn)
        else:
            await self._deleteDiscovery("switch", name)
        # note that _publishDiscovery does expect the state topic
        # but we have the command topic stored.

    def topic(self):
        return self._topic
