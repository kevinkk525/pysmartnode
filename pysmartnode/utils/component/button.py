# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-10 

__updated__ = "2019-10-20"
__version__ = "0.6"

from .switch import ComponentSwitch
from pysmartnode.utils.component import Component
from pysmartnode import config
import uasyncio as asyncio

_mqtt = config.getMQTT()


class ComponentButton(ComponentSwitch):
    """
    Generic Button class.
    Use it according to the template.
    It will activate a "single-shot" device that will be off after activation again.
    Otherwise it would be a Switch.
    """

    def __init__(self, component_name, version, command_topic=None, instance_name=None,
                 wait_for_lock=False, discover=True):
        """
        :param component_name: name of the component that is subclassing this switch (used for discovery and topics)
        :param version: version of the component module. will be logged over mqtt
        :param command_topic: command_topic of subclass which controls the switch state. optional.
        :param instance_name: name of the instance. If not provided will get composed of component_name<count>
        :param wait_for_lock: if True then every request waits for the lock to become available,
        meaning the previous device request has to finish before the new one is started.
        Otherwise the new one will get ignored.
        With a single-shot action it usually doesn't make sense to wait for the lock.
        """
        super().__init__(component_name, version, command_topic, instance_name, wait_for_lock,
                         discover, restore_state=False)
        # discover: boolean, if this component should publish its mqtt discovery.
        # This can be used to prevent combined Components from exposing underlying
        # hardware components like a power switch

    async def on(self):
        """Turn switch on. Can be used by other components to control this component"""
        if self.lock.locked() is True and self._wfl is False:
            return False
        async with self.lock:
            _mqtt.schedulePublish(self._topic[:-4], "ON", qos=1, retain=True, timeout=1,
                                  await_connection=False)
            # so device gets activated as quickly as possible
            self._state = True
            await self._on()
            self._state = False
            await asyncio.sleep(0)
            # to ensure first publish will be done before new publish in case _on() is fast
            await _mqtt.publish(self._topic[:-4], "OFF", qos=1, retain=True, timeout=1,
                                await_connection=False)
            return True

    async def off(self):
        """Only for compatibility as single-shot action has no off()"""
        return True

    async def toggle(self):
        """Just for compatibility reasons, will always activate single-shot action"""
        return await self.on()

    async def _off(self):
        """Only for compatibility as single-shot action has no _off()"""
        return True
