# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2019-09-10 

__updated__ = "2020-04-02"
__version__ = "0.91"

from .switch import ComponentSwitch
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

    def __init__(self, component_name, version, unit_index: int, wait_for_lock=False,
                 initial_state=False, **kwargs):
        """
        :param component_name: name of the component that is subclassing this switch (used for discovery and topics)
        :param version: version of the component module. will be logged over mqtt
        :param unit_index: counter of the registerd unit of this sensor_type (used for default topics)
        :param mqtt_topic: command_topic of subclass which controls the switch state. optional.
        :param instance_name: name of the instance. If not provided will get composed of component_name<count>
        :param wait_for_lock: if True then every request waits for the lock to become available,
        meaning the previous device request has to finish before the new one is started.
        Otherwise the new one will get ignored.
        With a single-shot action it usually doesn't make sense to wait for the lock.
        :param friendly_name: friendly name for homeassistant gui
        :param initial_state: the initial state of the button, typically False ("OFF") for Pushbutton
        """
        super().__init__(component_name, version, unit_index, wait_for_lock=wait_for_lock,
                         restore_state=False, initial_state=initial_state, **kwargs)

    async def on(self):
        """Turn Button on. Can be used by other components to control this component"""
        if self._lock.locked() is True and self._wfl is False:
            return False
        async with self._lock:
            if self._pub_task:
                self._pub_task.cancel()  # cancel if not finished, e.g. if activated quickly again
            self._pub_task = asyncio.create_task(self._publish("ON"))
            # so device gets activated as quickly as possible
            self._state = True
            await self._on()
            self._state = False
            if self._pub_task:
                self._pub_task.cancel()  # cancel if not finished, e.g. if _on() is very fast
            self._pub_task = asyncio.create_task(self._publish("OFF"))
            return True

    async def off(self):
        """Only for compatibility as single-shot action has no off()"""
        return True

    async def toggle(self):
        """Just for compatibility reasons, will always activate single-shot action"""
        return await self.on()
