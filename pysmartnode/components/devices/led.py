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

__updated__ = "2018-03-25"
__version__ = "2.3"

import gc

from machine import Pin
from pysmartnode import config
import uasyncio as asyncio

mqtt = config.getMQTT()

gc.collect()


class LEDNotification:
    def __init__(self, pin, on_time=50, off_time=50, iters=20, mqtt_topic=None):
        if type(pin) == str:
            pin = config.pins[pin]
        mqtt_topic = mqtt_topic or mqtt.getDeviceTopic("LEDNotification", is_request=True)
        self.pin = pin
        self.on_time = on_time
        self.off_time = off_time
        self.iters = iters
        self.lock = config.Lock()
        Pin(self.pin, Pin.OUT, value=0)
        mqtt.scheduleSubscribe(mqtt_topic, self.notification, check_retained=False)
        # not checking retained as buzzer only activates single-shot

    async def notification(self, topic, msg, retain):
        if self.lock.locked():
            return False
        async with self.lock:
            if msg in mqtt.payload_on:
                for i in range(0, self.iters):
                    Pin(self.pin, Pin.OUT).value(1)
                    await asyncio.sleep_ms(self.on_time)
                    Pin(self.pin, Pin.OUT).value(0)
                    await asyncio.sleep_ms(self.off_time)
        return False  # will not publish the state "ON" to mqtt
