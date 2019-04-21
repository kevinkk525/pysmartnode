# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-04-10 

__updated__ = "2019-04-21"
__version__ = "0.3"

"""
Simple water sensor using 2 wires in water. As soon as some conductivity is possible, the sensor will hit.

{
    package: .sensors.waterSensor
    component: WaterSensor
    constructor_args: {
        power_pin: 5
        adc: 33
        # interval: None            # optional, interval in seconds, defaults to 10minutes 
        # interval_reading: 1       # optional, interval in seconds that the sensor gets polled
        # cutoff_voltage: 3.3       # optional, defaults to ADC maxVoltage (on ESP 3.3V)
        # mqtt_topic: "sometopic"   # optional, defaults to home/<controller-id>/waterSensor/<count> 
    }
} 
Will publish on any state change and in the given interval. State changes are detected in the interval_reading.
Only the intervals of the first initialized sensors are used. 
This is to need only one uasyncio task for all sensors to prevent a uasyncio queue overflow.

** How to connect:
Put a Resistor (300R-2kR) between the power pin and the adc pin.
Connect the wires to the adc pin and gnd.
"""

from pysmartnode import config
from pysmartnode import logging
from pysmartnode.components.machine.adc import ADC
from pysmartnode.components.machine.pin import Pin
import uasyncio as asyncio
import gc
import machine
import time

_component_name = "WaterSensor"
_count = 0
_instances = []

_log = logging.getLogger(_component_name)
_mqtt = config.getMQTT()
gc.collect()


class WaterSensor:
    DEBUG = False

    def __init__(self, adc, power_pin, cutoff_voltage=None, interval=None, interval_reading=1, topic=None):
        interval = interval or config.INTERVAL_SEND_SENSOR
        self._adc = ADC(adc)
        self._ppin = Pin(power_pin, machine.Pin.OUT)
        self._cv = cutoff_voltage or self._adc.maxVoltage()
        global _instances
        if len(_instances) == 0:  # prevent loop queue overflow from multiple instances
            asyncio.get_event_loop().create_task(self._loop(interval_reading))
        _instances.append(self)
        global _count
        self._t = topic or _mqtt.getDeviceTopic("waterSensor/{!s}".format(_count))
        _count += 1
        self._lv = None
        self._tm = time.ticks_ms()
        self._int = interval * 1000

    @staticmethod
    async def _loop(interval_reading):
        interval_reading = interval_reading - 0.1 * len(_instances)
        if interval_reading < 0:
            interval_reading = 0
            # still has 100ms after every read
        while True:
            for inst in _instances:
                a = time.ticks_us()
                await inst.water()
                b = time.ticks_us()
                print("Water took", (b - a) / 1000, "ms")
                await asyncio.sleep_ms(100)
                # using multiple sensors connected to Arduinos it would result in long blocking calls
            await asyncio.sleep(interval_reading)

    async def _read(self, publish=True):
        self._ppin.value(1)
        vol = self._adc.readVoltage()
        if self.DEBUG is True:
            print("#{!s}, V".format(self._t[-1]), vol)
        self._ppin.value(0)
        if vol >= self._cv:
            state = False
            if publish is True and (time.ticks_diff(time.ticks_ms(), self._tm) > self._int or self._lv != state):
                await _mqtt.publish(self._t, "dry", retain=True)
                self._tm = time.ticks_ms()
            self._lv = state
            return False
        else:
            state = True
            if publish is True and (time.ticks_diff(time.ticks_ms(), self._tm) > self._int or self._lv != state):
                await _mqtt.publish(self._t, "wet", retain=True)
                self._tm = time.ticks_ms()
            self._lv = state
            return True

    async def water(self, publish=True):
        return await self._read(publish)
