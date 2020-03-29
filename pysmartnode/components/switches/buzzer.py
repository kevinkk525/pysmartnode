# Author: Kevin Köck
# Copyright Kevin Köck 2017-2020 Released under the MIT license
# Created on 2017-10-31

"""
example config:
{
    package: .switches.buzzer,
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

__updated__ = "2020-03-29"
__version__ = "3.3"

import gc
from machine import Pin, PWM
from pysmartnode.components.machine.pin import Pin as PyPin
from pysmartnode import config
import uasyncio as asyncio
from pysmartnode.utils.component.button import ComponentButton

_mqtt = config.getMQTT()

####################
# choose a component name that will be used for logging (not in leightweight_log),
# a default mqtt topic that can be changed by received or local component configuration
# as well as for the component name in homeassistant.
COMPONENT_NAME = "Buzzer"
####################


gc.collect()

_unit_index = -1


class Buzzer(ComponentButton):
    def __init__(self, pin, pwm_values, on_time=500, iters=1, freq=1000, mqtt_topic=None,
                 friendly_name=None, discover=True, **kwargs):
        self.pin = PyPin(pin, Pin.OUT)
        self.on_time = on_time
        self.values = pwm_values
        self.iters = iters
        self.pin = PWM(self.pin, freq=freq)
        self.pin.duty(0)
        # This makes it possible to use multiple instances of Buzzer
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, mqtt_topic, discover=discover,
                         **kwargs)
        self._frn = friendly_name
        gc.collect()

    async def _on(self):
        for _ in range(self.iters):
            for duty in self.values:
                self.pin.duty(duty)
                await asyncio.sleep_ms(self.on_time)
        self.pin.duty(0)
