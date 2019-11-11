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
        # interval_publish: -1      # optional, defaults to -1 because sensor will automatically publish on any state change. Can be changed for sending "keepalives" in between changes.
        # interval_reading: 1       # optional, interval in seconds that the sensor gets polled
        # cutoff_voltage: 3.3       # optional, defaults to ADC maxVoltage (on ESP 3.3V). Above this voltage means dry
        # mqtt_topic: "sometopic"   # optional, defaults to home/<controller-id>/waterSensor/<count>
        # friendly_name: null       # optional, friendly name for the homeassistant gui
        # discover: true            # optional, if false no discovery message for homeassistant will be sent.
        # expose_intervals: Expose intervals to mqtt so they can be changed remotely
        # intervals_topic: if expose_intervals then use this topic to change intervals. Defaults to <home>/<device-id>/<COMPONENT_NAME><_unit_index>/interval/set. Send a dictionary with keys "reading" and/or "publish" to change either/both intervals.
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

__updated__ = "2019-11-11"
__version__ = "1.6"

from pysmartnode import config
from pysmartnode import logging
from pysmartnode.components.machine.adc import ADC
from pysmartnode.components.machine.pin import Pin
import uasyncio as asyncio
import gc
import machine
import time
from pysmartnode.utils.component.sensor import ComponentSensor, SENSOR_BINARY_MOISTURE, \
    VALUE_TEMPLATE

COMPONENT_NAME = "WaterSensor"
_unit_index = -1

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()


class WaterSensor(ComponentSensor):
    DEBUG = False

    def __init__(self, adc, power_pin=None, cutoff_voltage=None, interval_publish=None,
                 interval_reading=1, mqtt_topic=None, friendly_name=None, discover=True,
                 expose_intervals=False, intervals_topic=None):
        interval_publish = interval_publish or -1
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, discover, interval_publish,
                         interval_reading, mqtt_topic, _log, expose_intervals, intervals_topic)
        self._adc = ADC(adc)
        self._ppin = Pin(power_pin, machine.Pin.OUT) if power_pin is not None else None
        self._cv = cutoff_voltage or self._adc.maxVoltage()
        self._lv = None
        self._addSensorType(SENSOR_BINARY_MOISTURE, 0, 0, VALUE_TEMPLATE, "", friendly_name,
                            mqtt_topic, None, True)
        self._pub_coro = None

    async def _read(self):
        a = time.ticks_us()
        p = self._ppin
        if p is not None:
            p.value(1)
        vol = self._adc.readVoltage()
        if self.DEBUG is True:
            print("#{!s}, V".format(self.getTopic(SENSOR_BINARY_MOISTURE)[-1]), vol)
        if p is not None:
            p.value(0)
        if vol >= self._cv:
            state = False
            if self._lv != state:
                # dry
                if self._pub_coro is not None:
                    self._pub_coro.cancel()
                self._pub_coro = asyncio.create_task(
                    _mqtt.publish(self.getTopic(SENSOR_BINARY_MOISTURE), "OFF", qos=1,
                                  retain=True, timeout=None, await_connection=True))

            self._lv = state
        else:
            state = True
            if self._lv != state:
                # wet
                if self._pub_coro is not None:
                    self._pub_coro.cancel()
                self._pub_coro = asyncio.create_task(_mqtt.publish(self.getTopic(SENSOR_BINARY_MOISTURE), "ON", qos=1,
                                               retain=True, timeout=None, await_connection=True))
            self._lv = state
        b = time.ticks_us()
        if WaterSensor.DEBUG:
            print("Water measurement took", (b - a) / 1000, "ms")
