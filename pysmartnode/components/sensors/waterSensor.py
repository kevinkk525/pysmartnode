# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-04-10

"""
Simple water sensor using 2 wires in water. As soon as some conductivity is possible, the sensor will hit.

{
    package: .sensors.waterSensor
    component: WaterSensor
    constructor_args: {
        adc: 33
        power_pin: 5                # optional if connected to permanent power
        # interval: None            # optional, interval in seconds, defaults to 10minutes 
        # interval_reading: 1       # optional, interval in seconds that the sensor gets polled
        # cutoff_voltage: 3.3       # optional, defaults to ADC maxVoltage (on ESP 3.3V). Above this voltage means dry
        # mqtt_topic: "sometopic"   # optional, defaults to home/<controller-id>/waterSensor/<count>
        # friendly_name: null       # optional, friendly name for the homeassistant gui
    }
} 
Will publish on any state change and in the given interval. State changes are detected in the interval_reading.
Only the polling interval of the first initialized sensor is used.
The publish interval is unique to each sensor. 
This is to use only one uasyncio task for all sensors to prevent a uasyncio queue overflow.

** How to connect:
Put a Resistor (~10kR) between the power pin (or permanent power) and the adc pin.
Connect the wires to the adc pin and gnd.
"""

__updated__ = "2019-10-11"
__version__ = "1.3"

from pysmartnode import config
from pysmartnode import logging
from pysmartnode.components.machine.adc import ADC
from pysmartnode.components.machine.pin import Pin
import uasyncio as asyncio
import gc
import machine
import time
from pysmartnode.utils.component import Component, DISCOVERY_BINARY_SENSOR

COMPONENT_NAME = "WaterSensor"
_COMPONENT_TYPE = "binary_sensor"
_count = 0
_instances = []

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()


class WaterSensor(Component):
    DEBUG = False

    def __init__(self, adc, power_pin=None, cutoff_voltage=None, interval=None,
                 interval_reading=1, topic=None, friendly_name=None, discover=True):
        super().__init__(COMPONENT_NAME, __version__, discover)
        self._ir = interval_reading
        self._adc = ADC(adc)
        self._ppin = Pin(power_pin, machine.Pin.OUT) if power_pin is not None else None
        self._cv = cutoff_voltage or self._adc.maxVoltage()
        global _instances
        _instances.append(self)
        global _count
        self._topic = topic or _mqtt.getDeviceTopic("waterSensor/{!s}".format(_count))
        self._count = _count
        _count += 1
        self._lv = None
        self._tm = time.ticks_ms()
        interval = interval or config.INTERVAL_SEND_SENSOR
        self._int = interval * 1000
        self._frn = friendly_name
        asyncio.get_event_loop().create_task(self._loop())

    async def _loop(self):
        if self._count == 0:
            # only the first sensor reads all sensors to prevent uasyncio queue overflow
            interval_reading = self._ir - 0.05 * len(_instances)
            if interval_reading < 0:
                interval_reading = 0
                # still has 100ms after every read
            while True:
                for inst in _instances:
                    a = time.ticks_us()
                    await inst.water()
                    b = time.ticks_us()
                    if WaterSensor.DEBUG:
                        print("Water measurement took", (b - a) / 1000, "ms")
                    await asyncio.sleep_ms(50)
                    # using multiple sensors connected to Arduinos it would result in
                    # long blocking calls because a single call to a pin takes ~17ms
                await asyncio.sleep(interval_reading)

    async def _discovery(self):
        name = "{!s}{!s}".format(COMPONENT_NAME, self._count)
        sens = DISCOVERY_BINARY_SENSOR.format("moisture")  # device_class
        await self._publishDiscovery(_COMPONENT_TYPE, self._topic, name, sens,
                                     self._frn or "Moisture")
        gc.collect()

    async def _read(self, publish=True, timeout=5):
        p = self._ppin
        if p is not None:
            p.value(1)
        vol = self._adc.readVoltage()
        if self.DEBUG is True:
            print("#{!s}, V".format(self._topic[-1]), vol)
        if p is not None:
            p.value(0)
        if vol >= self._cv:
            state = False
            if publish is True and (
                    time.ticks_diff(time.ticks_ms(), self._tm) > self._int or self._lv != state):
                await _mqtt.publish(self._topic, "OFF", qos=1, retain=True, timeout=timeout,
                                    await_connection=False)  # dry
                self._tm = time.ticks_ms()
            self._lv = state
            return False
        else:
            state = True
            if publish is True and (
                    time.ticks_diff(time.ticks_ms(), self._tm) > self._int or self._lv != state):
                await _mqtt.publish(self._topic, "ON", qos=1, retain=True, timeout=timeout,
                                    await_connection=False)  # wet
                self._tm = time.ticks_ms()
            self._lv = state
            return True

    async def water(self, publish=True, timeout=5):
        return await self._read(publish, timeout)

    @staticmethod
    def waterTemplate():
        return "{{ value }}"

    def waterTopic(self):
        return self._topic
