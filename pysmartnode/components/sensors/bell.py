# Author: Kevin Köck
# Copyright Kevin Köck 2017-2020 Released under the MIT license
# Created on 2017-10-29

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
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_last: null # optional, friendly name for last_bell
    }
}
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

__updated__ = "2020-04-07"
__version__ = "1.6"

import gc
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.locksync import Lock
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.component import ComponentBase, DISCOVERY_TIMELAPSE, VALUE_TEMPLATE
import machine
import time
import uasyncio as asyncio


class EventISR:
    # Event class from Peter Hinch used in uasyncio V2
    def __init__(self, delay_ms=0):
        self.delay_ms = delay_ms
        self.clear()

    def clear(self):
        self._flag = False
        self._data = None

    async def wait(self):  # CPython comptaibility
        while not self._flag:
            await asyncio.sleep_ms(self.delay_ms)

    def __await__(self):
        while not self._flag:
            await asyncio.sleep_ms(self.delay_ms)

    __iter__ = __await__

    def is_set(self):
        return self._flag

    def set(self, data=None):
        self._flag = True
        self._data = data

    def value(self):
        return self._data


COMPONENT_NAME = "Bell"

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()

gc.collect()


# TODO: make Bell inherit from ComponentSensor (like it is supposed to be in the category "sensors"

class Bell(ComponentBase):
    def __init__(self, pin, debounce_time, on_time=None, irq_direction=None, mqtt_topic=None,
                 friendly_name=None, friendly_name_last=None, **kwargs):
        super().__init__(COMPONENT_NAME, __version__, unit_index=0, logger=_log, **kwargs)
        self._topic = mqtt_topic
        self._PIN_BELL_IRQ_DIRECTION = irq_direction or machine.Pin.IRQ_FALLING
        self._debounce_time = debounce_time
        self._on_time = on_time or 500
        self._pin_bell = pin
        self._last_activation = 0
        self._frn = friendly_name
        self._frn_l = friendly_name_last
        self._event_bell = EventISR(delay_ms=20)
        self._event_bell.clear()
        self._timer_lock = Lock()
        if self._PIN_BELL_IRQ_DIRECTION == machine.Pin.IRQ_FALLING:
            self._pin_bell = Pin(self._pin_bell, machine.Pin.IN, machine.Pin.PULL_UP)
        else:
            self._pin_bell = Pin(self._pin_bell, machine.Pin.IN)
        self._pin_bell.irq(trigger=self._PIN_BELL_IRQ_DIRECTION, handler=self.__irqBell)
        self._timer_bell = machine.Timer(1)
        asyncio.create_task(self._loop())
        _log.info("Bell initialized")
        gc.collect()

    async def _loop(self):
        while True:
            await self._event_bell.wait()
            diff = time.ticks_diff(time.ticks_ms(), self._last_activation)
            if diff > 10000:
                _log.error("Bell rang {!s}s ago, not activated ringing".format(diff / 1000))
                self._event_bell.clear()
                return
            else:
                on = await _mqtt.publish(self.topic(), "ON", qos=1, timeout=2,
                                         await_connection=False)
                await asyncio.sleep_ms(self._on_time)
                await _mqtt.publish(self.topic(), "OFF", qos=1, retain=True, await_connection=on)
                if config.RTC_SYNC_ACTIVE:
                    t = time.localtime()
                    await _mqtt.publish(_mqtt.getDeviceTopic("last_bell"),
                                        "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1],
                                                                                       t[2], t[3],
                                                                                       t[4], t[5]),
                                        qos=1, retain=True, timeout=2, await_connection=False)
                self._event_bell.clear()
                if diff > 500:
                    _log.warn("Bell rang {!s}ms ago, activated ringing".format(diff))

    def __irqBell(self, p):
        if self._timer_lock.locked() is True or self._event_bell.is_set() is True:
            return
        else:
            self._timer_lock.acquire()  # not checking return value as we checked locked state above
            self._timer_bell.init(period=self._debounce_time,
                                  mode=machine.Timer.ONE_SHOT, callback=self.__irqTime)

    def __irqTime(self, t):
        if self._PIN_BELL_IRQ_DIRECTION == machine.Pin.IRQ_FALLING and self._pin_bell.value() == 0:
            self._last_activation = time.ticks_ms()
            self._event_bell.set()
        elif self._PIN_BELL_IRQ_DIRECTION == machine.Pin.IRQ_RISING and self._pin_bell.value() == 1:
            self._last_activation = time.ticks_ms()
            self._event_bell.set()
        self._timer_bell.deinit()
        self._timer_lock.release()

    async def _discovery(self, register=True):
        if register:
            await self._publishDiscovery("binary_sensor", self.getTopic(), "bell",
                                         '"ic":"mdi:bell",', self._frn or "Doorbell")
        else:
            await self._deleteDiscovery("binary_sensor", "bell")
        gc.collect()
        if config.RTC_SYNC_ACTIVE is True:
            if register:
                await self._publishDiscovery("sensor", _mqtt.getDeviceTopic("last_bell"),
                                             "last_bell", DISCOVERY_TIMELAPSE,
                                             self._frn_l or "Last Bell")
                gc.collect()
            else:
                await self._deleteDiscovery("sensor", "last_bell")

    def getTopic(self, *args, **kwargs):
        return self._topic or _mqtt.getDeviceTopic(COMPONENT_NAME)

    @staticmethod
    def getTemplate(self, *args, **kwargs):
        return VALUE_TEMPLATE

    @staticmethod
    def getValue(self, *args, **kwargs):
        return None
