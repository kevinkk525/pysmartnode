'''
Created on 30.10.2017

@author: Kevin Köck
'''

"""
example config:
{
    package: .switches.gpio
    component: GPIO
    constructor_args: {
        pin: D5
        active_high: true           #optional, defaults to active high
        # mqtt_topic: sometopic     #optional, topic needs to have /set at the end, defaults to <home>/<device-id>/GPIO/<pin>
        # friendly_name: "led"               #optional, custom name for the pin in homeassistant, defaults to "GPIO_<pin>"
    }
}
"""

__updated__ = "2019-09-10"
__version__ = "0.7"

import gc
import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode import config
from pysmartnode.utils.component.switch import ComponentSwitch, DISCOVERY_SWITCH

_mqtt = config.getMQTT()

_component_name = "GPIO"
_component_type = "switch"

gc.collect()


class GPIO(ComponentSwitch):
    def __init__(self, pin, active_high=True, mqtt_topic=None, friendly_name=None):
        mqtt_topic = mqtt_topic or _mqtt.getDeviceTopic("{!s}/{!s}".format(_component_name, str(pin)), is_request=True)
        super().__init__(_component_name, mqtt_topic, instance_name="{!s}_{!s}".format(_component_name, pin))
        self.pin = Pin(pin, machine.Pin.OUT, value=0 if active_high else 1)
        self._frn = friendly_name
        self._active_high = active_high

    async def _on(self):
        self.pin.value(1 if self._active_high else 0)
        return True

    async def _off(self):
        self.pin.value(0 if self._active_high else 1)
        return True
