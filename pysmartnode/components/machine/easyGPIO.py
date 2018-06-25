'''
Created on 30.10.2017

@author: Kevin Köck
'''

"""
example config:
{
    package: .machine.easyGPIO
    component: gpio
    constructor_args: {
        #mqtt_topic: null   #optional, topic needs to have /GPIO/# at the end; to change a value publish to /GPIO/<pin>/set
    }
}
makes esp8266 listen to requested gpio changes or return pin.value() if message is published without payload
"""

__updated__ = "2018-03-22"
__version__ = "0.3"

import gc

from machine import Pin
from pysmartnode import config
from pysmartnode import logging

log = logging.getLogger("easyGPIO")
mqtt = config.getMQTT()

gc.collect()


async def __gpio(topic, msg, retain):
    if topic.rfind("/set") == -1:
        if retain:
            pin = topic[topic.rfind("GPIO/") + 5:]
        else:
            # topic without /set ignored if not retained
            return False
    else:
        pin = topic[topic.rfind("GPIO/") + 5:topic.rfind("/set")]
    print("__gpio pin", pin, msg, retain)
    try:
        pin = int(pin)
    except:
        # means that pin is a str
        try:
            pin = config.pins[pin]
        except:
            log.error("pin {!r} does not exist".format(pin))
            return False
    if msg != "":
        value = None
        if msg in mqtt.payload_on:
            value = 1
        elif msg in mqtt.payload_off:
            value = 0
        try:
            value = int(msg)
        except:
            pass
        if value is None:
            log.error("pin {!r} got no supported value {!r}".format(pin, msg))
            return False
        Pin(pin, Pin.OUT).value(value)
        return True
    else:
        return Pin(pin, Pin.IN).value()


def gpio(topic=None):
    topic = topic or mqtt.getDeviceTopic("GPIO/#")
    print("gpio", topic)
    mqtt.scheduleSubscribe(topic, __gpio)
