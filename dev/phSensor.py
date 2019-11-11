# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-05-11 

"""
example config:
{
    package: .sensors.phSensor
    component: PHsensor
    constructor_args: {
        adc: 22                     # ADC object/pin number
        adc_multi: 1.52             # ADC multiplicator when using voltage divider (needed on esp when sensor probe not connected as voltage goes to 5V then)
        precision: 2                # precision of the pH value published
        voltage_calibration_0: 2.54  # voltage at pH value #0
        pH_calibration_value_0: 6.86 # pH value for calibration point #0
        voltage_calibration_1: 3.04  # voltage at pH value #1
        pH_calibration_value_1: 4.01 # pH value for calibration point #1
        # interval: 600             # optional, defaults to 600. -1 means do not automatically read sensor and publish values
        # mqtt_topic: sometopic     # optional, defaults to home/<controller-id>/PHsensor
        # friendly_name: null       # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
Inspiration from: https://scidle.com/how-to-use-a-ph-sensor-with-arduino/

Example measurements:
situation,  real,   esp
shorted,    2.61    2.5
destilled   2.73    2.6
ph4.01      3.14    3.0
ph6.86      2.68    2.53

growing solution 3.24    3.1  (this is very wrong.., ph actually ~5.2)
"""

__updated__ = "2019-11-01"
__version__ = "0.6"

from pysmartnode import config
from pysmartnode.components.machine.adc import ADC
from pysmartnode import logging
import uasyncio as asyncio
from pysmartnode.utils.component import Component
import gc

COMPONENT_NAME = "PHsensor"
_COMPONENT_TYPE = "sensor"

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_unit_index = -1

PH_TYPE = '"unit_of_meas":"pH",' \
          '"val_tpl":"{{ value|float }}",' \
          '"ic":"mdi:alpha-p-circle-outline"'
_VAL_T_ACIDITY = "{{ value|float }}"


class PHsensor(Component):
    def __init__(self, adc, adc_multi, voltage_calibration_0, pH_calibration_value_0,
                 voltage_calibration_1, pH_calibration_value_1,
                 precision=2, interval=None, mqtt_topic=None,
                 friendly_name=None, discover=True):
        # This makes it possible to use multiple instances of MySensor
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, discover)
        self._interval = interval or config.INTERVAL_SENSOR_PUBLISH
        self._topic = mqtt_topic
        self._frn = friendly_name
        self._adc = ADC(adc)
        self._adc_multi = adc_multi

        self.__ph = None

        self._prec = int(precision)

        self._v0 = voltage_calibration_0
        self._v1 = voltage_calibration_1
        self._ph0 = pH_calibration_value_0
        self._ph1 = pH_calibration_value_1
        gc.collect()
        if self._interval > 0:  # if interval==-1 no loop will be started
            asyncio.create_task(self._loop())

    async def _loop(self):
        interval = self._interval
        while True:
            self.__ph = await self._read()
            await asyncio.sleep(interval)

    async def _discovery(self, register=True):
        name = "{!s}{!s}".format(COMPONENT_NAME, self._count)
        if register:
            await self._publishDiscovery(_COMPONENT_TYPE, self.acidityTopic(), name, PH_TYPE,
                                         self._frn or "pH")
        else:
            await self._deleteDiscovery(_COMPONENT_TYPE, name)

    async def _read(self, publish=True, timeout=5) -> float:
        buf = []
        for _ in range(10):
            buf.append(self._adc.readVoltage() * self._adc_multi)
            await asyncio.sleep_ms(50)
        buf.remove(max(buf))
        buf.remove(max(buf))
        buf.remove(min(buf))
        buf.remove(min(buf))
        v = 0
        for i in range(len(buf)):
            v += buf[i]
        v /= len(buf)
        ph1 = self._ph1
        ph0 = self._ph0
        v0 = self._v0
        v1 = self._v1
        m = (ph1 - ph0) / (v1 - v0)
        b = (ph0 * v1 - ph1 * v0) / (v1 - v0)
        print("U", v)
        print("m", m)
        print("b", b)
        value = m * v + b
        value = round(value, self._prec)
        print("pH", value)
        if value > 14:
            await _log.asyncLog("error",
                                "Not correctly connected, voltage {!s}, ph {!s}".format(v, value))
            return None
        if publish:
            await _mqtt.publish(self.acidityTopic(),
                                ("{0:." + str(self._prec) + "f}").format(value),
                                timeout=timeout, await_connection=False)
        return value

    async def acidity(self, publish=True, timeout=5, no_stale=False) -> float:
        if self._interval == -1 or no_stale:
            return await self._read(publish, timeout)
        return self.__ph

    @staticmethod
    def acidityTemplate():
        """Other components like HVAC might need to know the value template of a sensor"""
        return _VAL_T_ACIDITY

    def acidityTopic(self):
        return self._topic or _mqtt.getDeviceTopic("{!s}{!s}".format(COMPONENT_NAME, self._count))
