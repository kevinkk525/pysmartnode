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
        mqtt_topic: sometopic     #optional, topic needs to have /set at the end
    }
}
"""

__updated__ = "2018-08-18"
__version__ = "0.3"

import gc
import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode import config
from pysmartnode import logging

_mqtt = config.getMQTT()

gc.collect()


class GPIO:
    def __init__(self, pin, mqtt_topic=None):
        mqtt_topic = mqtt_topic or _mqtt.getDeviceTopic("GPIO/" + str(pin), is_request=True)
        self.pin = Pin(pin, machine.Pin.OUT, value=0)
        _mqtt.scheduleSubscribe(mqtt_topic, self.setValue)

    # publishing is done by mqtt class as long as topic has "/set" at the end
    async def setValue(self, topic, msg, retain):
        _log = logging.getLogger("gpio")
        if msg != "":
            if msg in _mqtt.payload_on:
                self.pin.value(1)
                return True
            elif msg in _mqtt.payload_off:
                self.pin.value(0)
                return True
            else:
                _log.error("Unknown payload {!r}, GPIO {!s}".format(msg, self.pin))
                return False
        else:
            _log.error("No message for GPIO {!s}".format(self.pin))
            return False
