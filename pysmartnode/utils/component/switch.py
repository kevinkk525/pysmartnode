# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2019-09-10 

__updated__ = "2020-04-01"
__version__ = "1.6"

from pysmartnode.utils.component import ComponentBase
from .definitions import DISCOVERY_SWITCH
from pysmartnode import config
import gc
import uasyncio as asyncio

_mqtt = config.getMQTT()


class ComponentSwitch(ComponentBase):
    """
    Generic Switch class.
    Use it according to the template.
    """

    def __init__(self, component_name, version, unit_index: int, mqtt_topic: str = None,
                 instance_name=None, wait_for_lock=True, restore_state=True,
                 friendly_name=None, initial_state=None, **kwargs):
        """
        :param mqtt_topic: topic of subclass which controls the switch state. optional. If not ending with "/set", it will be added as the command_topic is being stored.
        :param instance_name: name of the instance. If not provided will get composed of component_name<count>
        :param wait_for_lock: if True then every request waits for the lock to become available,
        :param restore_state: restore the retained state topic state
        meaning the previous device request has to finish before the new one is started.
        Otherwise the new one will get ignored.
        :param friendly_name: friendly name for homeassistant gui
        :param initial_state: intitial state of the switch. By default unknown so first state change request will set initial state.
        """
        super().__init__(component_name, version, unit_index, **kwargs)
        self._state = initial_state  # initial state is unknown if None
        if mqtt_topic and not mqtt_topic.endswith("/set"):
            mqtt_topic = "{}{}".format(mqtt_topic, "/set")
        self._topic = mqtt_topic or _mqtt.getDeviceTopic(
            "{!s}{!s}/set".format(component_name, self._count))
        _mqtt.subscribeSync(self._topic, self.on_message, self, check_retained_state=restore_state)
        self._lock = asyncio.Lock()
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
            self._event = asyncio.Event()
        return self._event

    def _setState(self, state: bool):
        if state != self._state and self._event is not None:
            self._event.set()
        self._state = state

    async def on_message(self, topic, msg, retain):
        """
        Standard callback to change the device state from mqtt.
        Can be subclassed if extended functionality is needed.
        """
        if msg in _mqtt.payload_on:
            if not self._state:  # False or None (unknown)
                await self.on()  # no return because state will be published by on()/off()
        elif msg in _mqtt.payload_off:
            if self._state is not False:  # True or None (unknown)
                await self.off()  # no return because state will be published by on()/off()
        else:
            raise TypeError("Payload {!s} not supported".format(msg))
        return False  # will not publish the requested state to mqtt as already done by on()/off()

    async def _publish(self, msg):
        await _mqtt.publish(self._topic[:-4], msg, qos=1, retain=True)
        self._pub_task = None

    async def on(self) -> bool:
        """Turn switch on. Can be used by other components to control this component"""
        if self._lock.locked() and not self._wfl:
            return False
        async with self._lock:
            return await self.__on()

    async def __on(self) -> bool:
        res = await self._on()  # if _on() returns True the value should be published
        if res is True:
            self._setState(True)
            if self._pub_task:
                self._pub_task.cancel()
                self._pub_task = None
            self._pub_task = asyncio.create_task(self._publish("ON"))
        return res

    async def off(self) -> bool:
        """Turn switch off. Can be used by other components to control this component"""
        if self._lock.locked() and not self._wfl:
            return False
        async with self._lock:
            return await self.__off()

    async def __off(self) -> bool:
        res = await self._off()  # if _off() returns True the value should be published
        if res is True:
            self._setState(False)
            if self._pub_task:
                self._pub_task.cancel()
                self._pub_task = None
            self._pub_task = asyncio.create_task(self._publish("OFF"))
        return res

    async def toggle(self) -> bool:
        """Toggle device state. Can be used by other component to control this component"""
        if self._wfl:
            await self._lock.acquire()
        elif self._lock.locked() and not self._wfl:
            return False
        try:
            if self._state is True:
                return await self.off()
            else:
                return await self.on()
        finally:
            if self._wfl:
                self._lock.release()

    def state(self) -> bool:
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

    def topic(self) -> str:
        """Returns the topic of the component. Note that it returns the command_topic!"""
        return self._topic
