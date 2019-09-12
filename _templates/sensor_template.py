'''
Created on 14.04.2018

@author: Kevin Köck
'''

"""
example config:
{
    package: <package_path>
    component: MySensor
    constructor_args: {
        i2c: i2c                   #i2c object created before
        precision_temp: 2         #precision of the temperature value published
        precision_humid: 1        #precision of the humid value published
        offset_temp: 0            #offset for temperature to compensate bad sensor reading offsets
        offset_humid: 0           #...             
        # interval: 600            #optional, defaults to 600
        # mqtt_topic: sometopic  #optional, defaults to home/<controller-id>/HTU
        # friendly_name_temp: null    # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_humid: null    # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
"""

__updated__ = "2019-05-11"
__version__ = "1.0"

from pysmartnode import config
from pysmartnode.utils.wrappers.async_wrapper import async_wrapper as _async_wrapper
from pysmartnode import logging
import uasyncio as asyncio
from pysmartnode.utils.component import Component, DISCOVERY_SENSOR
import gc

####################
# import your library here
from htu21d import HTU21D as Sensor

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "HTU"
# define the type of the component according to the homeassistant specifications
_COMPONENT_TYPE = "sensor"
####################

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_count = 0


class MySensor(Component):
    def __init__(self, i2c, precision_temp=2, precision_humid=1,  # extend or shrink according to your sensor
                 offset_temp=0, offset_humid=0,  # also here
                 interval=None, mqtt_topic=None,
                 friendly_name_temp=None, friendly_name_humid=None):
        super().__init__()
        self._interval = interval or config.INTERVAL_SEND_SENSOR
        self._topic = mqtt_topic or _mqtt.getDeviceTopic(COMPONENT_NAME)
        self._frn_temp = friendly_name_temp
        self._frn_humid = friendly_name_humid

        # This makes it possible to use multiple instances of MySensor
        global _count
        self._count = _count
        _count += 1

        ##############################
        # adapt to your sensor by extending/removing unneeded values like in the constructor arguments
        self._prec_temp = int(precision_temp)
        self._prec_humid = int(precision_humid)
        ###
        self._offs_temp = float(offset_temp)
        self._offs_humid = float(offset_humid)
        ##############################
        # create sensor object
        self.sensor = Sensor(i2c=i2c)  # add neccessary constructor arguments here
        ##############################
        # create a link to the functions of the sensor
        # (if that function is a coroutine you can omit _async_wrapper)
        self._temp = _async_wrapper(self.sensor.temperature)
        self._humid = _async_wrapper(self.sensor.humidity)
        ##############################
        # choose a background loop that periodically reads the values and publishes it
        # (function is created below)
        self._background_loop = self.tempHumid
        ##############################
        gc.collect()

    async def _init(self):
        await super()._init()
        gen = self._background_loop
        interval = self._interval
        while True:
            await gen()
            await asyncio.sleep(interval)
        # only start a loop in _init if its only purpose is to publish to mqtt because
        # otherwise the code might never get started if connection to network/mqtt fails.

    async def _discovery(self):
        component_topic = self._topic  # get the state topic of custom component topic
        # In this case the component_topic has to be set to self._topic as the humidity and temperature
        # are going to be published from the same topic.

        for v in (("T", "Temperature", "°C", "{{ value_json.temperature}}", self._frn_temp),
                  ("H", "Humidity", "%", "{{ value_json.humidity}}", self._frn_humid)):
            name = "{!s}{!s}{!s}".format(COMPONENT_NAME, self._count, v[0])
            # note that the name needs to be unique for temperature and humidity as they are
            # different components in the homeassistant gui.
            sens = DISCOVERY_SENSOR.format(v[1].lower(),  # device_class
                                           v[2],  # unit_of_measurement
                                           v[3])  # value_template
            await self._publishDiscovery(_COMPONENT_TYPE, component_topic, name, sens, v[4] or v[1])
            del name, sens
            gc.collect()

    async def _read(self, coro, prec, offs, publish=True):
        if coro is None:
            raise TypeError("Sensor generator is of type None")
        try:
            value = await coro()
        except Exception as e:
            _log.error("Error reading sensor {!s}: {!s}".format(COMPONENT_NAME, e))
            return None
        if value is not None:
            value = round(value, prec)
            value += offs
        if value is None:
            _log.warn("Sensor {!s} got no value".format(COMPONENT_NAME))
        elif publish:
            await _mqtt.publish(self._topic, ("{0:." + str(prec) + "f}").format(value))
        return value

    ##############################
    # remove or add functions below depending on the values of your sensor

    async def temperature(self, publish=True):
        return await self._read(self._temp, self._prec_temp, self._offs_temp, publish)

    async def humidity(self, publish=True):
        return await self._read(self._humid, self._prec_humid, self._offs_humid, publish)

    async def tempHumid(self, publish=True):
        temp = await self.temperature(publish=False)
        humid = await self.humidity(publish=False)
        if temp is not None and humid is not None and publish:
            await _mqtt.publish(self._topic, {
                "temperature": ("{0:." + str(self._prec_temp) + "f}").format(temp),
                "humidity":    ("{0:." + str(self._prec_humid) + "f}").format(humid)})
            # formating prevents values like 51.500000000001 on esp32_lobo
        return {"temperature": temp, "humiditiy": humid}

    ##############################
