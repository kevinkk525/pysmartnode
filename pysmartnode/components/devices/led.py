'''
Created on 28.10.2017

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.led
    component: LEDNotification
    constructor_args: {
        pin: D5
        #on_time: 50      #optional, time led is on, defaults to 50ms
        #off_time: 50      #optional, time led is off, defaults to 50ms
        #iters: 20        #optional, iterations done, defaults to 20
        #mqtt_topic: null     #optional, topic needs to have /set at the end
    }
}
"""

__updated__ = "2018-09-26"
__version__ = "2.6"

import gc

import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode import config
import uasyncio as asyncio

_mqtt = config.getMQTT()

gc.collect()


class LEDNotification:
    def __init__(self, pin, on_time=50, off_time=50, iters=20, mqtt_topic=None):
        mqtt_topic = mqtt_topic or _mqtt.getDeviceTopic("LEDNotification", is_request=True)
        self.pin = Pin(pin, machine.Pin.OUT, value=0)
        self.on_time = on_time
        self.off_time = off_time
        self.iters = iters
        self.lock = config.Lock()

        _mqtt.scheduleSubscribe(mqtt_topic, self.notification, check_retained_state_topic=False)
        # not checking retained as led only activates single-shot
        self.mqtt_topic = mqtt_topic

    async def notification(self, topic, msg, retain):
        if self.lock.locked():
            return False
        async with self.lock:
            if msg in _mqtt.payload_on:
                _mqtt.schedulePublish(self.mqtt_topic, "ON")
                for i in range(0, self.iters):
                    self.pin.value(1)
                    await asyncio.sleep_ms(self.on_time)
                    self.pin.value(0)
                    await asyncio.sleep_ms(self.off_time)
                await _mqtt.publish(self.mqtt_topic, "OFF")
        return False  # will not publish the state "ON" to mqtt
