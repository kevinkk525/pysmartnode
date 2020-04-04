# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2019-03-31

"""
Datasheet: https://www.mpja.com/download/hc-sr04_ultrasonic_module_user_guidejohn.pdf

Warning: My sensor only read distances reliable with flat surfaces within 80cm. 
Above that the results were fluctuating heavily.
A stable power source seems to be helpful.

example config:
{
    package: .sensors.hcsr04
    component: HCSR04
    constructor_args: {
        pin_trigger: D5
        pin_echo: D6
        # timeout: 30000        # optional, defaults to 30000 which is around sensor maximum distance. Can be used to discard values that are beyond the expected result anyway.
        # temp_sensor: "ds18"   # optional, name of temperature sensor if temperature compensated measurement is needed
        # precision: 2          # precision of the distance value published
        # offset: 0             # offset for distance value to compensate bad sensor reading offsets
        # sleeping_time: 200     # optional, sleeping time between reading iterations
        # iterations: 20        # optional, reading iterations per sensor reading
        # percentage_failed_readings_abort: 0.66 # optional, if a higher percentage of readings was bad, the current reading will be aborted
        # value_template: "{{ 60.0 - float(value) }}" # optional, can be used to measure the reverse distance (e.g. water level)
        # friendly_name: "Distance" # optional, friendly name for homeassistant gui by mqtt discovery
    }
}
HC-SR04 ultrasonic sensor.
Be sure to connect it to 5V but use a voltage divider to connect the Echo pin to an ESP.
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

__updated__ = "2020-03-31"
__version__ = "0.92"

from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.component.sensor import ComponentSensor, SENSOR_TEMPERATURE, \
    VALUE_TEMPLATE_FLOAT
from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import machine
import time
import gc

COMPONENT_NAME = "hcsr04"

DISCOVERY_DISTANCE = '"unit_of_meas":"cm",' \
                     '"val_tpl":"{{ value|float }}",' \
                     '"ic":"mdi:axis-arrow",'

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_unit_index = -1


class HCSR04(ComponentSensor):
    def __init__(self, pin_trigger, pin_echo, timeout=30000, temp_sensor: ComponentSensor = None,
                 precision: int = 2, offset: float = 0, sleeping_time: int = 20,
                 iterations: int = 30, percentage_failed_readings_abort: float = 0.66,
                 value_template=None, friendly_name=None, **kwargs):
        """
        HC-SR04 ultrasonic sensor.
        Be sure to connect it to 5V but use a voltage divider to connect the Echo pin to an ESP.
        :param pin_trigger: pin number/object of trigger pin
        :param pin_echo: pin number/object of echo pin
        :param timeout: reading timeout, corresponds to sensor limit range of 4m
        :param temp_sensor: temperature sensor object
        :param precision: int, precision of distance value published and returned
        :param offset: float, distance value offset, shouldn't be needed
        :param sleeping_time: int, sleeping time between reading iterations
        :param iterations: int, reading iterations per sensor reading
        :param percentage_failed_readings_abort: float, if a higher percentage of readings was bad, the reading will be aborted
        :param value_template: optional template can be used to measure the reverse distance (e.g. water level)
        :param friendly_name: friendly name for homeassistant gui by mqtt discovery, defaults to "Distance"
        """
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, logger=_log, **kwargs)
        self._tr = Pin(pin_trigger, mode=machine.Pin.OUT)
        self._tr.value(0)
        self._ec = Pin(pin_echo, mode=machine.Pin.IN)
        self._to = timeout
        self._sleep = sleeping_time
        self._iters = iterations
        self._pfr = percentage_failed_readings_abort
        if temp_sensor is not None:
            self.checkSensorType(temp_sensor, SENSOR_TEMPERATURE)
        self._temp: ComponentSensor = temp_sensor
        self._addSensorType("distance", precision, offset, value_template or VALUE_TEMPLATE_FLOAT,
                            "cm", friendly_name, discovery_type=DISCOVERY_DISTANCE)

    def _pulse(self) -> int:
        """
        Send a pulse and wait for the echo pin using machine.time_pulse_us() to measure us.
        :return: int
        """
        tr = self._tr
        tr.value(0)
        time.sleep_us(5)
        tr.value(1)
        time.sleep_us(10)
        tr.value(0)
        try:
            return machine.time_pulse_us(self._ec, 1, self._to)
        except OSError as e:
            if e.args[0] == 100:  # TIMEOUT
                raise OSError("Object too far")
            raise e

    async def _read(self):
        if self._temp is not None:
            temp = await self._temp.getValue(SENSOR_TEMPERATURE, publish=self._intrd > 5,
                                             timeout=5 if self._intrd > 20 else 0)
            if temp is None:  # only log errors if reading interval allows it
                await _log.asyncLog("warn",
                                    "Couldn't read temp sensor, using fallback calculation",
                                    timeout=10 if self._intrd > 20 else 0)
        else:
            temp = None
        val = []
        diffs = []
        warnings = 0  # probably not going to happen that both warning types occur at the same time
        warning = "minimum distance reached or different problem"
        for _ in range(self._iters):
            try:
                a = time.ticks_us()
                pt = self._pulse()
                b = time.ticks_us()
                if pt > 175:  # ~3cm, sensor minimum distance, often read although other problems
                    val.append(pt)
                    diffs.append(time.ticks_diff(b, a))
                else:
                    warnings += 1
            except OSError as e:
                warning = e
                warnings += 1
            await asyncio.sleep_ms(self._sleep)
        if warnings > self._iters * self._pfr:  # self._pbr sensor readings are bad
            if config.DEBUG:
                print("HCSR04 len readings", len(val), "/", self._iters, "sleep", self._sleep)
                print("HCSR04 readings", val)
                print("HCSR04 t_diffs:", diffs)
            await self._setValue("distance", None, log_error=False)
            await _log.asyncLog("error",
                                "Too many bad sensor readings, error:", warning,
                                timeout=10 if self._intrd > 20 else 0)
            return
        # removing extreme values until only 5-6 remain
        val2 = [v for v in val]
        while len(val) >= 7:
            val.remove(max(val))
            val.remove(min(val))
        pt = sum(val) / len(val)
        if temp is None:
            dt = (pt / 2) / 29.14
        else:
            dt = (pt / 2) * ((331.5 + (0.6 * temp)) / 10000)
        if config.DEBUG:
            print("HCSR04 distance", dt, "temp ", temp, "len readings", len(val2), "/",
                  self._iters, "sleep", self._sleep)
            print("HCSR04 readings", val2)
            print("HCSR04 t_diffs:", diffs)
            print("HCSR04 used readings", val)
        if dt < 0:
            await self._setValue("distance", None, log_error=False)
            await _log.asyncLog("warn", "Sensor reading <0", timeout=10 if self._intrd > 20 else 0)
            return
        await self._setValue("distance", dt, timeout=10 if self._intrd > 20 else 0)
