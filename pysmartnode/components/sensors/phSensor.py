# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
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
    }
}
Inspiration from: https://scidle.com/how-to-use-a-ph-sensor-with-arduino/

Example measurements:

"""

__updated__ = "2021-05-27"
__version__ = "0.7"

from pysmartnode import config
from pysmartnode.components.machine.adc import ADC
from pysmartnode import logging
import uasyncio as asyncio
from pysmartnode.utils.component.sensor import ComponentSensor
import gc

COMPONENT_NAME = "PHsensor"
_COMPONENT_TYPE = "sensor"

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_unit_index = -1

DISCOVERY_PH = '"unit_of_meas":"pH",' \
          '"val_tpl":"{{ value|float }}",' \
          '"ic":"mdi:alpha-p-circle-outline",'
_VAL_T_ACIDITY = "{{ value|float }}"


class PHsensor(ComponentSensor):
    def __init__(self, adc, voltage_calibration_0, pH_calibration_value_0,
                 voltage_calibration_1, pH_calibration_value_1, adc_multi=1,
                 precision=2, offset=0, friendly_name=None, **kwargs):
        # This makes it possible to use multiple instances of MySensor
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, logger=_log, **kwargs)
        self._adc = ADC(adc)
        self._adc_multi = adc_multi
        self._v0 = voltage_calibration_0
        self._v1 = voltage_calibration_1
        self._ph0 = pH_calibration_value_0
        self._ph1 = pH_calibration_value_1
        self._addSensorType("pH", precision, offset, _VAL_T_ACIDITY, "pH",
                            friendly_name or "pH-Wert", self._topic, DISCOVERY_PH)
        gc.collect()

    async def _read(self):
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
        print("pH", round(value,2))
        if value > 14:
            await _log.asyncLog("error",
                                "Not correctly connected, voltage {!s}, ph {!s}".format(v, value))
            await self._setValue("pH", None, log_error=False)
        await self._setValue("pH", value)
