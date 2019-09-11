# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-10 

__updated__ = "2019-09-10"
__version__ = "0.1"

from pysmartnode.utils.component import Component
from .definitions import DISCOVERY_SWITCH
from pysmartnode import config
import uasyncio as asyncio
import gc

_mqtt = config.getMQTT()


class ComponentButton(Component):
    """
    Generic Button class.
    Use it according to the template.
    It will activate a "single-shot" device that will be off after activation again.
    Otherwise it would be a Switch.
    """

    def __init__(self, component_name, command_topic=None, instance_name=None, wait_for_lock=False):
        """
        :param component_name: name of the component that is subclassing this switch (used for discovery and topics)
        :param command_topic: command_topic of subclass which controls the switch state. optional.
        :param instance_name: name of the instance. If not provided will get composed of component_name<count>
        :param wait_for_lock: if True then every request waits for the lock to become available,
        meaning the previous device request has to finish before the new one is started.
        Otherwise the new one will get ignored.
        """
        super().__init__()
        self._topic = command_topic or _mqtt.getDeviceTopic("{!s}{!s}".format(component_name, self._count),
                                                            is_request=True)
        # not subscribing here as we don't need the retained state topic as it should always be "OFF"
        self.lock = config.Lock()  # in case switch activates a device that will need a while to finish
        self._wfl = wait_for_lock
        self._component_name = component_name
        self._name = instance_name
        gc.collect()

    async def _init(self):
        await super()._init()
        self._subscribe(self._topic, self.on_message)
        await _mqtt.subscribe(self._topic, check_retained_state_topic=False)

    async def on_message(self, topic, msg, retain):
        """
        Standard callback to change the device state from mqtt.
        Can be subclassed if extended functionality is needed.
        """
        if self.lock.locked() is True and self._wfl is False:
            return False
        async with self.lock:
            if msg in _mqtt.payload_on:
                _mqtt.schedulePublish(self._topic[:-4], "ON", qos=1, retain=True)
                # so device gets activated as quickly as possible
                await self._on()
                await asyncio.sleep(0)  # to ensure first publish will be done before new publish in case _on() is fast
                await _mqtt.publish(self._topic[:-4], "OFF", qos=1, retain=True)
                return False
            elif msg in _mqtt.payload_off:
                return True  # "OFF" will be published automatically.
            else:
                raise TypeError("Payload {!s} not supported".format(msg))
        return False  # will not publish the requested state to mqtt

    async def on(self):
        """Turn switch on. Can be used by other components to control this component"""
        _mqtt.schedulePublish(self._topic[:-4], "ON", qos=1, retain=True)
        # so device gets activated as quickly as possible
        await self._on()
        await asyncio.sleep(0)  # to ensure first publish will be done before new publish in case _on() is fast
        await _mqtt.publish(self._topic[:-4], "OFF", qos=1, retain=True)
        return True

    @staticmethod
    async def off():
        """Only for compatibility as single-shot action has no off()"""
        return True

    async def toggle(self):
        """Just for compatibility reasons, will always activate single-shot action"""
        return await self.on()

    async def _discovery(self):
        name = self._name or "{!s}{!s}".format(self._component_name, self._count)
        await self._publishDiscovery("switch", self._topic[:-4], name, DISCOVERY_SWITCH, self._frn)
        # note that _publishDiscovery does expect the state topic but we have the command topic stored.
