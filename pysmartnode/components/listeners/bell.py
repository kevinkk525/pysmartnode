'''
Created on 29.10.2017

@author: Kevin Köck
'''

"""
example config:
{
    package: .sensors.bell
    component: Bell
    constructor_args: {
        pin: D5
        debounce_time: 20      #ms
        on_time: 500 #ms       #optional, time the mqtt message stays at on
        direction: 2           #optional, falling 2 (pull-up used in code), rising 1, 
        #mqtt_topic: sometopic #optional, defaults to home/bell
    }
}
"""

__updated__ = "2018-06-01"
__version__ = "0.4"

import gc
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.event import Event
import machine
import time
import uasyncio as asyncio

log = logging.getLogger("bell")
mqtt = config.getMQTT()

gc.collect()


class Bell:
    def __init__(self, pin, debounce_time, on_time=None, irq_direction=None, mqtt_topic=None):
        self.mqtt_topic = mqtt_topic or "{!s}/bell".format(config.MQTT_HOME)
        self.PIN_BELL_IRQ_DIRECTION = irq_direction or machine.Pin.IRQ_FALLING
        self.debounce_time = debounce_time
        self.on_time = on_time or 500
        self.pin_bell = pin if type(pin) != str else config.pins[pin]
        self.last_activation = 0
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.__initializeBell())
        gc.collect()

    async def __initializeBell(self):
        if self.PIN_BELL_IRQ_DIRECTION == machine.Pin.IRQ_FALLING:
            self.pin_bell = machine.Pin(self.pin_bell, machine.Pin.IN, machine.Pin.PULL_UP)
        else:
            self.pin_bell = machine.Pin(self.pin_bell, machine.Pin.IN)
        self.eventBell = Event()
        self.timerLock = Event(onTrue=False)
        irq = self.pin_bell.irq(trigger=self.PIN_BELL_IRQ_DIRECTION, handler=self.__irqBell)
        self.eventBell.clear()
        self.loop.create_task(self.__bell())
        self.timer_bell = machine.Timer(1)
        log.info("Bell initialized")
        gc.collect()

    async def __bell(self):
        while True:
            await self.eventBell
            diff = time.ticks_diff(time.ticks_ms(), self.last_activation)
            if diff > 10000:
                log.error("Bell rang {!s}s ago, not activated ringing".format(diff / 1000))
                self.eventBell.clear()
                return
            else:
                await mqtt.publish(self.mqtt_topic, "ON", qos=1)
                await asyncio.sleep_ms(self.on_time)
                await mqtt.publish(self.mqtt_topic, "OFF", True, 1)
                if config.RTC_SYNC_ACTIVE:
                    t = time.localtime()
                    await mqtt.publish("{!s}/last_bell".format(config.MQTT_HOME),
                                       "{} {}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format("GMT", t[0],
                                                                                         t[1], t[2],
                                                                                         t[3], t[4],
                                                                                         t[5]), True, 1)
                self.eventBell.clear()
                if diff > 500:
                    log.warn("Bell rang {!s}ms ago, activated ringing".format(diff))

    def __irqBell(self, p):
        # print("BELL",p)
        # print("BELL",time.ticks_ms())
        if self.timerLock.is_set() == True or self.eventBell.is_set() == True:
            return
        else:
            self.timerLock.set()
            self.timer_bell.init(period=self.debounce_time,
                                 mode=machine.Timer.ONE_SHOT, callback=self.__irqTime)

    def __irqTime(self, t):
        # print("timer",time.ticks_ms())
        if self.PIN_BELL_IRQ_DIRECTION == machine.Pin.IRQ_FALLING and self.pin_bell.value() == 0:
            self.last_activation = time.ticks_ms()
            self.eventBell.set()
        elif self.PIN_BELL_IRQ_DIRECTION == machine.Pin.IRQ_RISING and self.pin_bell.value() == 1:
            self.last_activation = time.ticks_ms()
            self.eventBell.set()
        self.timer_bell.deinit()
        self.timerLock.clear()
