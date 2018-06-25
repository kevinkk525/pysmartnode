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

__updated__ = "2018-03-25"
__version__ = "0.1"

import gc

from machine import Pin
from pysmartnode import config
from pysmartnode import logging

mqtt = config.getMQTT()

log = logging.getLogger("gpio")
gc.collect()


class GPIO:
    def __init__(self, pin, mqtt_topic=None):
        if type(pin) == str:
            pin = config.pins[pin]
        mqtt_topic = mqtt_topic or mqtt.getDeviceTopic("GPIO/" + str(pin), is_request=True)
        self.pin = pin
        Pin(self.pin, Pin.OUT, value=0)
        mqtt.scheduleSubscribe(mqtt_topic, self.setValue)

    # publishing is done by mqtt class as long as topic has "/set" at the end
    async def setValue(self, topic, msg, retain):
        if msg != "":
            if msg in mqtt.payload_on:
                Pin(self.pin, Pin.OUT).value(1)
                return True
            elif msg in mqtt.payload_off:
                Pin(self.pin, Pin.OUT).value(0)
                return True
            else:
                log.error("Unknown payload {!r}, GPIO {!s}".format(msg, self.pin))
                return False
        else:
            log.error("No message for GPIO {!s}".format(self.pin))
            return False
