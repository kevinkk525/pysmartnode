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

__updated__ = "2018-09-28"
__version__ = "0.6"

import gc
import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode import config
from pysmartnode import logging

_mqtt = config.getMQTT()

gc.collect()


async def __gpio(topic, msg, retain):
    _log = logging.getLogger("easyGPIO")
    if topic.endswith("/set") is False:
        if retain:
            pin = topic[topic.rfind("GPIO/") + 5:]
        else:
            # topic without /set ignored if not retained
            return False
    else:
        pin = topic[topic.rfind("GPIO/") + 5:topic.rfind("/set")]
    print("__gpio pin", pin, msg, retain)
    try:
        _p = Pin(pin)
    except Exception as e:
        await _log.logAsync("pin {!r} does not exist: {!s}".format(pin, e))
        return False
    if msg != "":
        value = None
        if msg in _mqtt.payload_on:
            value = 1
        elif msg in _mqtt.payload_off:
            value = 0
        try:
            value = int(msg)
        except:
            pass
        if value is None:
            await _log.logAsync("error", "pin {!r} got no supported value {!r}".format(pin, msg))
            return False
        Pin(pin, machine.Pin.OUT).value(value)
        return True
    else:
        return Pin(pin, machine.Pin.IN).value()


async def gpio(topic=None):
    topic = topic or _mqtt.getDeviceTopic("GPIO/#")
    await _mqtt.subscribe(topic, __gpio)
