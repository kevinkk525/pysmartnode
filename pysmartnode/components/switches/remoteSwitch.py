# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2019-10-11

"""
example config:
{
    package: .sensors.remoteSensors.switch
    component: RemoteSwitch
    constructor_args: {
        command_topic: sometopic      # command topic of the remote sensor
        state_topic: sometopic        # state topic of the remote sensor
        # timeout: 10                 # optional, defaults to 10s, timeout for receiving an answer
    }
}
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

# TODO: implement possibility to set sensor topics through mqtt, similar to RemoteSensor implementation
# TODO: make a real ComponentSwitch class so type checks won't fail

__updated__ = "2020-03-29"
__version__ = "0.3"

COMPONENT_NAME = "RemoteSwitch"

from pysmartnode.utils.component import ComponentBase
from pysmartnode import config
import uasyncio as asyncio
import time
from micropython import const

_mqtt = config.getMQTT()
_TIMEOUT = const(10)  # wait for a single reconnect but should be short enough if not connected
_unit_index = -1


class RemoteSwitch(ComponentBase):
    """
    Generic Switch class.
    Use it according to the template.
    """

    def __init__(self, command_topic, state_topic, timeout=_TIMEOUT, **kwargs):
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, discover=False, **kwargs)
        self._state = False
        self._topic = command_topic
        self._state_topic = state_topic
        self.lock = asyncio.Lock()
        # in case switch activates a device that will need a while to finish
        self._state_time = 0
        self._timeout = timeout
        _mqtt.subscribeSync(self._state_topic, self.on_message, self)

    async def on_message(self, topic, msg, retain):
        """
        Standard callback to change the device state from mqtt.
        Can be subclassed if extended functionality is needed.
        """
        if msg in _mqtt.payload_on:
            self._state = True
            self._state_time = time.ticks_ms()
        elif msg in _mqtt.payload_off:
            self._state = False
            self._state_time = time.ticks_ms()
        else:
            raise TypeError("Payload {!s} not supported".format(msg))
        return False  # will not publish the requested state to mqtt as already done by on()/off()

    async def on(self):
        """Turn switch on. Can be used by other components to control this component"""
        async with self.lock:
            t = time.ticks_ms()
            await _mqtt.publish(self._topic, "ON", qos=1, timeout=self._timeout)
            while time.ticks_diff(time.ticks_ms(), t) < self._timeout * 1000:
                if t < self._state_time:  # received new state
                    return self._state
            return False  # timeout reached

    async def off(self):
        """Turn switch off. Can be used by other components to control this component"""
        async with self.lock:
            t = time.ticks_ms()
            await _mqtt.publish(self._topic, "OFF", qos=1, timeout=self._timeout)
            while time.ticks_diff(time.ticks_ms(), t) < self._timeout * 1000:
                if t < self._state_time:  # received new state
                    return True if self._state is False else False
            return False  # timeout reached

    async def toggle(self):
        """Toggle device state. Can be used by other component to control this component"""
        if self._state is True:
            return await self.off()
        else:
            return await self.on()

    def state(self):
        return self._state

    def topic(self):
        return self._topic
