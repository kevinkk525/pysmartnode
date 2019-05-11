'''
Created on 30.10.2017

@author: Kevin Köck
'''

"""
example config:
{
    package: .machine.gpio
    component: GPIO
    constructor_args: {
        pin: D5
        # mqtt_topic: sometopic     #optional, topic needs to have /set at the end, defaults to <home>/<device-id>/GPIO/<pin>
        # friendly_name: "led"               #optional, custom name for the pin in homeassistant, defaults to "GPIO_<pin>"
    }
}
"""

__updated__ = "2019-04-29"
__version__ = "0.4"

import gc
import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.component import Component, DISCOVERY_SWITCH

_mqtt = config.getMQTT()

_component_name = "GPIO"
_component_type = "switch"

gc.collect()


class GPIO(Component):
    def __init__(self, pin, mqtt_topic=None, friendly_name=None):
        super().__init__()
        mqtt_topic = mqtt_topic or _mqtt.getDeviceTopic("{!s}/{!s}".format(_component_name, str(pin)), is_request=True)
        self._topic = mqtt_topic
        self._subscribe(self._topic)
        self.pin = Pin(pin, machine.Pin.OUT, value=0)
        self._frn = friendly_name
        self._name = "{!s}_{!s}".format(_component_name, pin)

    async def _discovery(self):
        await self._publishDiscovery(_component_type, self._topic[:-4], self._name, DISCOVERY_SWITCH, self._frn)

    async def on_message(self, topic, msg, retained):
        _log = logging.getLogger("gpio")
        if msg in _mqtt.payload_on:
            self.pin.value(1)
            return True
        elif msg in _mqtt.payload_off:
            self.pin.value(0)
            return True
        else:
            _log.error("Unknown payload {!r}, GPIO {!s}".format(msg, self.pin))
            return False
        # on "return True" mqtt will publish the state to the state topic
