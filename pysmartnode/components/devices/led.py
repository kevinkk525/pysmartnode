'''
Created on 28.10.2017

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.led
    component: LEDNotification
    constructor_args: {
        pin: D5
        #on_time: 50      #optional, time led is on, defaults to 50ms
        #off_time: 50      #optional, time led is off, defaults to 50ms
        #iters: 20        #optional, iterations done, defaults to 20
        #mqtt_topic: null     #optional, topic needs to have /set at the end
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
"""

__updated__ = "2019-07-05"
__version__ = "2.8"

import gc

import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode import config
import uasyncio as asyncio
from pysmartnode.utils.component import Component, DISCOVERY_SWITCH

_mqtt = config.getMQTT()

####################
# choose a component name that will be used for logging (not in leightweight_log),
# a default mqtt topic that can be changed by received or local component configuration
# as well as for the component name in homeassistant.
_component_name = "LEDNotification"
# define the type of the component according to the homeassistant specifications
_component_type = "switch"
####################

gc.collect()

_count = 0


class LEDNotification(Component):
    def __init__(self, pin, on_time=50, off_time=50, iters=20, mqtt_topic=None, friendly_name=None):
        super().__init__()
        self.pin = Pin(pin, machine.Pin.OUT, value=0)
        self.on_time = on_time
        self.off_time = off_time
        self.iters = iters
        self.lock = config.Lock()
        # This makes it possible to use multiple instances of LED
        global _count
        self._count = _count
        _count += 1
        mqtt_topic = mqtt_topic or _mqtt.getDeviceTopic("{!s}{!s}".format(_component_name, self._count),
                                                        is_request=True)
        self._topic = mqtt_topic
        self._frn = friendly_name
        gc.collect()

    async def _init(self):
        await super()._init()
        self._subscribe(self._topic, self.on_message)
        await _mqtt.subscribe(self._topic, check_retained_state_topic=False)
        # not checking retained state as led only activates single-shot and default state is always off

    async def on_message(self, topic, msg, retain):
        if self.lock.locked():
            return False
        async with self.lock:
            if msg in _mqtt.payload_on:
                _mqtt.schedulePublish(self._topic[:-4], "ON", qos=1)
                for i in range(0, self.iters):
                    self.pin.value(1)
                    await asyncio.sleep_ms(self.on_time)
                    self.pin.value(0)
                    await asyncio.sleep_ms(self.off_time)
                await _mqtt.publish(self._topic[:-4], "OFF", qos=1, retain=True)
        return False  # will not publish the state "ON" to mqtt

    async def _discovery(self):
        name = "{!s}{!s}".format(_component_name, self._count)
        await self._publishDiscovery(_component_type, self._topic[:-4], name, DISCOVERY_SWITCH, self._frn)
