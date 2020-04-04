# Author: Kevin Köck
# Copyright Kevin Köck 2017-2020 Released under the MIT license
# Created on 2017-10-30

"""
example config:
{
    package: .switches.gpio
    component: GPIO
    constructor_args: {
        pin: D5
        active_high: true           #optional, defaults to active high
        # mqtt_topic: sometopic     #optional, topic needs to have /set at the end, defaults to <home>/<device-id>/GPIO/<pin>
        # instance_name: name       #optional, name of the gpio instance, will be generated automatically
    }
}
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

__updated__ = "2020-04-03"
__version__ = "1.11"

import gc
import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode import config
from pysmartnode.utils.component.switch import ComponentSwitch

_mqtt = config.getMQTT()

COMPONENT_NAME = "GPIO"
_COMPONENT_TYPE = "switch"
_unit_index = -1

gc.collect()


class GPIO(ComponentSwitch):
    def __init__(self, pin, active_high=True, mqtt_topic=None, instance_name=None, **kwargs):
        mqtt_topic = mqtt_topic or _mqtt.getDeviceTopic(
            "{!s}/{!s}".format(COMPONENT_NAME, str(pin)), is_request=True)
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, mqtt_topic=mqtt_topic,
                         instance_name=instance_name or "{!s}_{!s}".format(COMPONENT_NAME, pin),
                         **kwargs)
        self.pin = Pin(pin, machine.Pin.OUT, value=0 if active_high else 1)
        self._state = not active_high
        self._active_high = active_high

    async def _on(self):
        self.pin.value(1 if self._active_high else 0)
        return True

    async def _off(self):
        self.pin.value(0 if self._active_high else 1)
        return True
