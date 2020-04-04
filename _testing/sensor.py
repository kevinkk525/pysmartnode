# Author: Kevin Köck
# Copyright Kevin Köck 2020 Released under the MIT license
# Created on 2020-04-02

__updated__ = "2020-04-02"
__version__ = "0.2"

from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.component.sensor import ComponentSensor, SENSOR_TEMPERATURE, SENSOR_HUMIDITY
import gc
import time

####################
# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "TestSensor"
# define (homeassistant) value templates for all sensor readings
_VAL_T_TEMPERATURE = "{{ value_json.temperature }}"
_VAL_T_HUMIDITY = "{{ value_json.humidity }}"
####################

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_unit_index = -1


class Sensor(ComponentSensor):
    def __init__(self, interval_reading=0.05, interval_publish=5, publish_old_values=True,
                 discover=False, **kwargs):
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, logger=_log, discover=discover,
                         interval_reading=interval_reading, interval_publish=interval_publish,
                         publish_old_values=publish_old_values, **kwargs)
        # discover: boolean, if this component should publish its mqtt discovery.
        # This can be used to prevent combined Components from exposing underlying
        # hardware components like a power switch

        self._addSensorType(SENSOR_TEMPERATURE, 0, 0, _VAL_T_TEMPERATURE, "°C")
        self._addSensorType(SENSOR_HUMIDITY, 0, 0, _VAL_T_HUMIDITY, "%")

        ##############################
        gc.collect()
        self._i = 0

    async def _read(self):
        t = self._i
        h = self._i
        _log.debug(time.ticks_ms(), self._i, local_only=True)
        self._i += 1
        await self._setValue(SENSOR_TEMPERATURE, t)
        await self._setValue(SENSOR_HUMIDITY, h)
