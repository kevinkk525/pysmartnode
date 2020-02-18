# Author: Kevin Köck
# Copyright Kevin Köck 2017-2019 Released under the MIT license
# Created on 2017-10-30

"""
example config:
{
    package: .machine.easyGPIO
    component: GPIO
    constructor_args: {
        # mqtt_topic: null   #optional, topic needs to have /easyGPIO/# at the end; to change a value publish to /easyGPIO/<pin>/set
        # discover_pins: [1,2,3] # optional, discover all pins of the list. Otherwise no pins are discovered.
    }
}
Makes esp8266 listen to requested gpio changes or return pin.value() if message is published without payload.
This component is just a generic interface to device pins, it does not offer ComponentSwitch features.
"""

__updated__ = "2019-11-07"
__version__ = "1.8"

import gc
import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.component import Component, DISCOVERY_SWITCH

_mqtt = config.getMQTT()

COMPONENT_NAME = "easyGPIO"
_COMPONENT_TYPE = "switch"

gc.collect()


class GPIO(Component):
    def __init__(self, mqtt_topic=None, discover_pins=None):
        super().__init__(COMPONENT_NAME, __version__, unit_index=0)
        self._topic = mqtt_topic or _mqtt.getDeviceTopic("easyGPIO/+/set")
        _mqtt.subscribeSync(self._topic, self.on_message, self, check_retained_state=True)
        self._d = discover_pins or []

    async def _discovery(self, register=True):
        for pin in self._d:
            name = "{!s}_{!s}".format(COMPONENT_NAME, pin)
            if register:
                await self._publishDiscovery(_COMPONENT_TYPE, "{}{}".format(self._topic[:-5], pin),
                                             name, DISCOVERY_SWITCH)
            else:
                await self._deleteDiscovery(_COMPONENT_TYPE, name)

    @staticmethod
    async def on_message(topic, msg, retain):
        _log = logging.getLogger("easyGPIO")
        if topic.endswith("/set") is False:
            if retain:
                pin = topic[topic.rfind("easyGPIO/") + 9:]
            else:
                # topic without /set ignored if not retained
                return False
        else:
            pin = topic[topic.rfind("easyGPIO/") + 9:-4]
        print("__gpio pin", pin, msg, retain)
        try:
            _p = Pin(pin)
        except Exception as e:
            await _log.asyncLog("pin {!r} does not exist: {!s}".format(pin, e))
            return False
        if msg != "":
            if msg in _mqtt.payload_on:
                value = 1
            elif msg in _mqtt.payload_off:
                value = 0
            else:
                try:
                    value = int(msg)
                except ValueError:
                    value = None
            if value is None:
                await _log.logAsync("error",
                                    "pin {!r} got no supported value {!r}".format(pin, msg))
                return False
            Pin(pin, machine.Pin.OUT).value(value)
            return True
        else:
            return Pin(pin, machine.Pin.IN).value()
