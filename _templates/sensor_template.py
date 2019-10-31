# Author: Kevin Köck
# Copyright Kevin Köck 2018-2019 Released under the MIT license
# Created on 2018-04-14

"""
example config:
{
    package: <package_path>
    component: MySensor
    constructor_args: {
        i2c: i2c                     # i2c object created before. this is just some custom sensor specific option
        precision_temp: 2            # precision of the temperature value published
        precision_humid: 1           # precision of the humid value published
        temp_offset: 0               # offset for temperature to compensate bad sensor reading offsets
        humid_offset: 0              # ...
        # interval_publish: 600      # optional, defaults to 600. Set to interval_reading to publish with every reading
        # interval_reading: 120      # optional, defaults to 120. -1 means do not automatically read sensor and publish values
        # mqtt_topic: sometopic      # optional, defaults to home/<controller-id>/HTU<count>
        # friendly_name_temp: null   # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_humid: null  # optional, friendly name shown in homeassistant gui with mqtt discovery
        # discover: true             # optional, if false no discovery message for homeassistant will be sent.
        # expose_intervals: false    # optional, expose intervals to mqtt so they can be changed remotely
        # intervals_topic: null      # optional, if expose_intervals then use this topic to change intervals. Defaults to <home>/<device-id>/<COMPONENT_NAME><_count>/interval/set. Send a dictionary with keys "reading" and/or "publish" to change either/both intervals.
    }
}
"""

__updated__ = "2019-10-30"
__version__ = "2.1"

from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.component.sensor import ComponentSensor, SENSOR_TEMPERATURE, SENSOR_HUMIDITY
import gc

####################
# import your library here
from htu21d import HTU21D as Sensor

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "HTU"
# define (homeassistant) value templates for all sensor readings
_VAL_T_TEMPERATURE = "{{ value_json.temperature }}"
_VAL_T_HUMIDITY = "{{ value_json.humidity }}"
####################

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_count = 0


class MySensor(ComponentSensor):
    def __init__(self, i2c, precision_temp=2, precision_humid=1,
                 temp_offset=0, humid_offset=0,  # extend or shrink according to your sensor
                 interval_publish=None, interval_reading=None, mqtt_topic=None,
                 friendly_name_temp=None, friendly_name_humid=None,
                 discover=True, expose_intervals=False, intervals_topic=None):
        """
        :param i2c: i2c object for temperature sensor
        :param precision_temp: precision of the temperature value, digits after separator "."
        :param precision_humid: precision of the humidity value, digits after separator "."
        :param temp_offset: float offset to account for bad sensor readings
        :param humid_offset:  float offset to account for bad sensor readings
        :param interval_publish: seconds, set to interval_reading to publish every reading. -1 for not publishing.
        :param interval_reading: seconds, set to -1 for not reading/publishing periodically. >0 possible for reading, 0 not allowed for reading.
        If reading interval is lower than the timeout of publishing all sensor readings would be,
        a separate publish coroutine will be started so the reading interval won't be impacted.
        :param mqtt_topic: optional custom mqtt topic, defaults to <home>/<device-id>/<COMPONENT_NAME><_count>
        :param friendly_name_temp: friendly name in homeassistant GUI for temperature component
        :param friendly_name_humid: friendly name in homeassistant GUI for humidity component
        :param discover: if the sensor component should send its homeassistnat discovery message
        :param expose_intervals: Expose intervals to mqtt so they can be changed remotely
        :param intervals_topic: if expose_intervals then use this topic to change intervals.
        Defaults to <home>/<device-id>/<COMPONENT_NAME><_count>/interval/set
        Send a dictionary with keys "reading" and/or "publish" to change either/both intervals.
        """
        super().__init__(COMPONENT_NAME, __version__, discover, interval_publish, interval_reading,
                         mqtt_topic, _log, expose_intervals, intervals_topic)
        # discover: boolean, if this component should publish its mqtt discovery.
        # This can be used to prevent combined Components from exposing underlying
        # hardware components like a power switch

        self._addSensorType(SENSOR_TEMPERATURE, precision_temp, temp_offset, _VAL_T_TEMPERATURE,
                            "°C", friendly_name_temp)
        self._addSensorType(SENSOR_HUMIDITY, precision_humid, humid_offset, _VAL_T_HUMIDITY, "%",
                            friendly_name_humid)

        # This makes it possible to use multiple instances of MySensor and have unique identifier
        global _count
        self._count = _count
        _count += 1

        ##############################
        # create sensor object
        self.sensor = Sensor(i2c=i2c)  # add neccessary constructor arguments here
        ##############################
        gc.collect()

    async def _read(self):
        t = await self.sensor.temperature()
        h = await self.sensor.humidity()
        await self._setValue(SENSOR_TEMPERATURE, t)
        await self._setValue(SENSOR_HUMIDITY, h)
