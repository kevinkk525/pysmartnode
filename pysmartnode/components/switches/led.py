'''
Created on 28.10.2017

@author: Kevin K�ck
'''

"""
example config:
{
    package: .switches.led
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

__updated__ = "2019-09-10"
__version__ = "3.0"

import gc

import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode import config
import uasyncio as asyncio
from pysmartnode.utils.component.button import ComponentButton

_mqtt = config.getMQTT()

####################
# choose a component name that will be used for logging (not in leightweight_log),
# a default mqtt topic that can be changed by received or local component configuration
# as well as for the component name in homeassistant.
_component_name = "LEDNotification"
####################

gc.collect()

_count = 0


class LEDNotification(ComponentButton):
    def __init__(self, pin, on_time=50, off_time=50, iters=20, mqtt_topic=None, friendly_name=None):
        self.pin = Pin(pin, machine.Pin.OUT, value=0)
        self.on_time = on_time
        self.off_time = off_time
        self.iters = iters
        # This makes it possible to use multiple instances of LED
        global _count
        self._count = _count
        _count += 1
        super().__init__(_component_name, mqtt_topic)
        self._frn = friendly_name
        gc.collect()

    async def _on(self):
        for i in range(0, self.iters):
            self.pin.value(1)
            await asyncio.sleep_ms(self.on_time)
            self.pin.value(0)
            await asyncio.sleep_ms(self.off_time)