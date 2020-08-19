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
        direction: 2      # optional, falling 2 (ring on GND), rising 1 (ring on Vcc)
        pull_up: true         # optional, if pin should be initialized as pull_up
        confirmations: 1      # optional, will read the pin value this often during debounce_time. (e.g. to ensure that a state is solid when having a pulsating/AC signal)
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_last: null # optional, friendly name for last_bell
    }
}
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

__updated__ = "2020-08-18"
__version__ = "2.2"

import gc
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.component.sensor import ComponentSensor, DISCOVERY_TIMELAPSE
import machine
import time
import uasyncio as asyncio

_DISCOVERY_BELL = '"expire_after":"0",'
COMPONENT_NAME = "Bell"

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_unit_index = -1


class Bell(ComponentSensor):
    def __init__(self, pin, debounce_time, on_time=None, direction=None, pull_up=True,
                 friendly_name=None, friendly_name_last=None, confirmations=1, **kwargs):
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, logger=_log,
                         interval_reading=0.001, interval_publish=0.001, expose_intervals=False,
                         **kwargs)
        self._low_active = True if direction == 2 else False
        self._debounce_time = debounce_time
        self._on_time = on_time or 500
        self._pin_bell = Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP if pull_up else None)
        self._timer_delay = 0
        self._last_activation = 0
        self._confirmations = confirmations
        self._active = False
        gc.collect()
        self._addSensorType("bell", friendly_name=friendly_name, binary_sensor=True,
                            discovery_type=_DISCOVERY_BELL, retained_publication=True,
                            topic=_mqtt.getDeviceTopic("bell{!s}".format(self._count)))
        self._addSensorType("last_bell", friendly_name=friendly_name_last,
                            topic=_mqtt.getDeviceTopic("last_bell{!s}".format(self._count)),
                            discovery_type=DISCOVERY_TIMELAPSE, retained_publication=True)
        _log.info("Bell initialized")
        gc.collect()

    async def _read(self):
        if self._active:
            # if bell was active, wait the on_time and reset the state to publish "off"
            await asyncio.sleep_ms(
                self._on_time - time.ticks_diff(time.ticks_ms(), self.getTimestamp("bell")))
            await self._setValue("bell", False)
            self._active = False
            print(time.ticks_us(), "loop cleared event")
            return
        # print(time.ticks_us(), "loop awaiting pin value change")
        while self._pin_bell.value() == self._low_active:
            await asyncio.sleep_ms(20)
        self._timer_delay = time.ticks_us()
        self._last_activation = time.ticks_ms()
        # print(time.ticks_us(), "loop pin value changed")
        sl = int(self._debounce_time / self._confirmations)
        diff = []
        await asyncio.sleep_ms(sl)
        for _ in range(0, self._confirmations):
            diff.append(time.ticks_diff(time.ticks_us(), self._timer_delay))
            value = self._pin_bell.value()
            # print(time.ticks_us(), "Timer took", diff / 1000, "ms, pin value", value)
            if value == self._low_active:
                print(time.ticks_us(), "pin value didn't stay")
                print(diff)
                return False  # return False so no value gets published
            self._timer_delay = time.ticks_us()
            await asyncio.sleep_ms(sl)
        print(time.ticks_us(), "pin change confirmed")
        print(diff)
        diff = time.ticks_diff(time.ticks_ms(), self._last_activation)
        if diff > 10000:
            _log.error("Bell rang {!s}s ago, not activated ringing".format(diff / 1000))
            return False  # return False so no value gets published
        else:
            self._active = True
            await self._setValue("bell", True)
            t = time.localtime()
            await self._setValue("last_bell",
                                 "{}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1],
                                                                                t[2], t[3],
                                                                                t[4], t[5]))
            if diff > 500:
                _log.warn("Bell rang {!s}ms ago, activated ringing anyways".format(diff))
