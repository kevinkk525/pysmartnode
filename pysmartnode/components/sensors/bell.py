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
        debounce_time: 20     # ms
        on_time: 500 #ms      # optional, time the mqtt message stays at on
        irq_direction: 2      # optional, falling 2 (pull-up used in code), rising 1,
        confirmations: 1      # optional, will read the pin value this often during debounce_time. (e.g. to ensure that a state is solid when having a pulsating/AC signal)
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_last: null # optional, friendly name for last_bell
    }
}
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

__updated__ = "2020-08-14"
__version__ = "2.1"

import gc
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.component.sensor import ComponentSensor, DISCOVERY_TIMELAPSE
import machine
import time
import uasyncio as asyncio

_DISCOVERY_BELL = '"expire_after":"0",'


class EventISR:
    # Event class from Peter Hinch used in uasyncio V2
    def __init__(self, delay_ms=0):
        self.delay_ms = delay_ms
        self._flag = False

    def clear(self):
        self._flag = False

    async def wait(self):  # CPython comptaibility
        while not self._flag:
            await asyncio.sleep_ms(self.delay_ms)

    def __await__(self):
        while not self._flag:
            yield from asyncio.sleep_ms(self.delay_ms)

    __iter__ = __await__

    def is_set(self):
        return self._flag

    def set(self):
        self._flag = True


COMPONENT_NAME = "Bell"

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_unit_index = -1


class Bell(ComponentSensor):
    def __init__(self, pin, debounce_time, on_time=None, irq_direction=None,
                 friendly_name=None, friendly_name_last=None, timer=-1, confirmations=1,
                 **kwargs):
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, logger=_log,
                         interval_reading=0.001, interval_publish=0.001, expose_intervals=False,
                         **kwargs)
        self._PIN_BELL_IRQ_DIRECTION = irq_direction or machine.Pin.IRQ_FALLING
        self._debounce_time = debounce_time
        self._on_time = on_time or 500
        self._pin_bell = pin
        self._event_bell = EventISR(delay_ms=10)
        if self._PIN_BELL_IRQ_DIRECTION == machine.Pin.IRQ_FALLING:
            self._pin_bell = Pin(self._pin_bell, machine.Pin.IN, machine.Pin.PULL_UP)
        else:
            self._pin_bell = Pin(self._pin_bell, machine.Pin.IN)
        self._pin_bell.irq(trigger=self._PIN_BELL_IRQ_DIRECTION, handler=self.__irqBell)
        self._timer_delay = 0
        self._last_activation = 0
        self._confirmations = confirmations
        gc.collect()
        self._addSensorType("bell", friendly_name=friendly_name, binary_sensor=True,
                            discovery_type=_DISCOVERY_BELL,
                            topic=_mqtt.getDeviceTopic("bell{!s}".format(self._count)))
        self._addSensorType("last_bell", friendly_name=friendly_name_last,
                            topic=_mqtt.getDeviceTopic("last_bell{!s}".format(self._count)),
                            discovery_type=DISCOVERY_TIMELAPSE)
        _log.info("Bell initialized")
        gc.collect()

    async def _read(self):
        if self._event_bell.is_set():
            # if event is set, wait the on_time and reset the state to publish "off"
            await asyncio.sleep_ms(
                self._on_time - time.ticks_diff(time.ticks_ms(), self.getTimestamp("bell")))
            await self._setValue("bell", False)
            self._event_bell.clear()
            # print(time.ticks_us(), "loop cleared event")
            return
        # print(time.ticks_us(), "loop awaiting event")
        await self._event_bell.wait()
        # print(time.ticks_us(), "loop got event")
        sl = int(self._debounce_time / self._confirmations)
        for _ in range(0, self._confirmations):
            # diff = time.ticks_diff(time.ticks_us(), self._timer_delay)
            value = self._pin_bell.value()
            # print(time.ticks_us(), "Timer took", diff / 1000, "ms, pin value", value)
            if self._PIN_BELL_IRQ_DIRECTION == machine.Pin.IRQ_FALLING and value == 1 \
                    or self._PIN_BELL_IRQ_DIRECTION == machine.Pin.IRQ_RISING and value == 0:
                # print(time.ticks_us(), "pin value didn't stay")
                return False  # return False so no value gets published
            self._timer_delay = time.ticks_us()
            await asyncio.sleep_ms(sl)
        # print(time.ticks_us(), "irq confirmed")
        diff = time.ticks_diff(time.ticks_ms(), self._last_activation)
        if diff > 10000:
            _log.error("Bell rang {!s}s ago, not activated ringing".format(diff / 1000))
            self._event_bell.clear()
            return False  # return False so no value gets published
        else:
            await self._setValue("bell", True)
            t = time.localtime()
            await self._setValue("last_bell",
                                 "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1],
                                                                                t[2], t[3],
                                                                                t[4], t[5]))
            if diff > 500:
                _log.warn("Bell rang {!s}ms ago, activated ringing anyways".format(diff))

    def __irqBell(self, p):
        # print(time.ticks_us(), "irq bell", self._event_bell.is_set())
        if self._event_bell.is_set() is True:
            return
        # print("event set")
        self._timer_delay = time.ticks_us()
        self._event_bell.set()
        self._last_activation = time.ticks_ms()
