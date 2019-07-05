'''
Created on 31.10.2017

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.buzzer,
    component: Buzzer,
    constructor_args: {
        pin: D5,
        pwm_values: [512,819,1020,786]  #list of pwm dutys, on esp32 use percentage, max is 1024 on esp8266
        # on_time: 500                #optional, defaults to 500ms, time buzzer stays at one pwm duty
        # iters: 1                   #optional, iterations done, defaults to 1
        # freq: 1000                 #optional, defaults to 1000
        # mqtt_topic: null     #optional, defaults to <mqtt_home>/<device_id>/Buzzer<count>/set
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
"""

__updated__ = "2019-07-05"
__version__ = "2.9"

import gc

from machine import Pin, PWM
from pysmartnode.components.machine.pin import Pin as PyPin
from pysmartnode import config
import uasyncio as asyncio
from pysmartnode.utils.component import Component, DISCOVERY_SWITCH

_mqtt = config.getMQTT()

####################
# choose a component name that will be used for logging (not in leightweight_log),
# a default mqtt topic that can be changed by received or local component configuration
# as well as for the component name in homeassistant.
_component_name = "Buzzer"
# define the type of the component according to the homeassistant specifications
_component_type = "switch"
####################


gc.collect()

_count = 0


class Buzzer(Component):
    def __init__(self, pin, pwm_values, on_time=500, iters=1, freq=1000, mqtt_topic=None, friendly_name=None):
        super().__init__()

        self.pin = PyPin(pin, Pin.OUT)
        self.on_time = on_time
        self.values = pwm_values
        self.iters = iters
        self.lock = config.Lock()
        self.pin = PWM(self.pin, freq=freq)
        self.pin.duty(0)
        # This makes it possible to use multiple instances of Buzzer
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
        # not checking retained state as buzzer only activates single-shot and default state is always off

    async def on_message(self, topic, msg, retain):
        if self.lock.locked():
            return False
        async with self.lock:
            if msg in _mqtt.payload_on:
                _mqtt.schedulePublish(self._topic[:-4], "ON", qos=1)
                for i in range(0, self.iters):
                    for duty in self.values:
                        self.pin.duty(duty)
                        await asyncio.sleep_ms(self.on_time)
                self.pin.duty(0)
                await _mqtt.publish(self._topic[:-4], "OFF", qos=1, retain=True)
        return False  # will not publish the state "ON" to mqtt

    async def _discovery(self):
        name = "{!s}{!s}".format(_component_name, self._count)
        await self._publishDiscovery(_component_type, self._topic[:-4], name, DISCOVERY_SWITCH, self._frn)
