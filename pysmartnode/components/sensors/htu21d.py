'''
Created on 28.10.2017

@author: Kevin Köck
'''

"""
example config:
{
    package: .sensors.htu21d
    component: HTU21D
    constructor_args: {
        i2c: i2c                    # i2c object created before
        precision_temp: 2           # precision of the temperature value published
        precision_humid: 1          # precision of the humid value published
        temp_offset: 0              # offset for temperature to compensate bad sensor reading offsets
        humid_offset: 0             # ...             
        # interval: 600             # optional, defaults to 600
        # mqtt_topic: sometopic     # optional, defaults to home/<controller-id>/HTU0
        # friendly_name_temp: null  # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_humid: null # optional, friendly name shown in homeassistant gui with mqtt discovery 
    }
}
"""

__updated__ = "2019-09-29"
__version__ = "2.1"

import gc
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.component import Component, DISCOVERY_SENSOR
import uasyncio as asyncio

####################
# import your library here
from pysmartnode.libraries.htu21d.htu21d_async import HTU21D as htu

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "HTU"
# define the type of the component according to the homeassistant specifications
_COMPONENT_TYPE = "sensor"
####################

_mqtt = config.getMQTT()
gc.collect()

_count = 0


class HTU21D(htu, Component):
    def __init__(self, i2c, precision_temp, precision_humid,
                 temp_offset, humid_offset,
                 mqtt_topic=None, interval=None,
                 friendly_name_temp=None, friendly_name_humid=None):
        Component.__init__(self, COMPONENT_NAME, __version__)
        self._interval = interval or config.INTERVAL_SEND_SENSOR
        # This makes it possible to use multiple instances of MySensor
        global _count
        self._count = _count
        _count += 1
        self._frn_temp = friendly_name_temp
        self._frn_humid = friendly_name_humid
        self._topic = mqtt_topic or _mqtt.getDeviceTopic(
            "{!s}/{!s}".format(COMPONENT_NAME, self._count))
        ##############################
        # adapt to your sensor by extending/removing unneeded values
        self._prec_temp = int(precision_temp)
        self._prec_humid = int(precision_humid)
        ###
        self._offs_temp = float(temp_offset)
        self._offs_humid = float(humid_offset)
        ##############################
        # create sensor object
        htu.__init__(self, i2c=i2c)
        ##############################
        # create a link to the functions of the sensor
        # (if that function is a coroutine you can omit _async_wrapper)
        self._temp = self.temperature_async
        self._humid = self.humidity_async
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

    async def _discovery(self):
        component_topic = self._topic  # get the state topic of custom component topic
        # In this case the component_topic has to be set to self._topic as the humidity and temperature
        # are going to be published from the same topic.
        for v in (("T", "Temperature", "°C", "{{ value_json.temperature}}", self._frn_temp),
                  ("H", "Humidity", "%", "{{ value_json.humidity}}", self._frn_humid)):
            name = "{!s}{!s}{!s}".format(COMPONENT_NAME, self._count, v[0])
            sens = DISCOVERY_SENSOR.format(v[1].lower(),  # device_class
                                           v[2],  # unit_of_measurement
                                           v[3])  # value_template
            await self._publishDiscovery(_COMPONENT_TYPE, component_topic, name, sens,
                                         v[4] or v[1])
            del name, sens
            gc.collect()

    async def _read(self, coro, prec, offs, publish=True, timeout=5):
        if coro is None:
            raise TypeError("Sensor generator is of type None")
        try:
            value = await coro()
        except Exception as e:
            await logging.getLogger(COMPONENT_NAME).asyncLog("error",
                                                             "Error reading sensor {!s}: {!s}".format(
                                                                 COMPONENT_NAME,
                                                                 e))
            return None
        if value is not None:
            value = round(value, prec)
            value += offs
        if publish and value is not None:
            await _mqtt.publish(self._topic, ("{0:." + str(prec) + "f}").format(value),
                                timeout=timeout, await_connection=False)
        return value

    async def temperature(self, publish=True, timeout=5):
        temp = await self._read(self._temp, self._prec_temp, self._offs_temp, publish, timeout)
        if temp is not None and temp < -48:
            # on a device without a connected HTU I sometimes get about -48.85
            if publish:
                await logging.getLogger(COMPONENT_NAME).asyncLog("warn",
                                                                 "Sensor {!s} got no value".format(
                                                                     COMPONENT_NAME))
            return None
        return temp

    async def humidity(self, publish=True, timeout=5):
        humid = await self._read(self._humid, self._prec_humid, self._offs_humid, publish, timeout)
        if humid is not None and humid <= 5:
            # on a device without a connected HTU I sometimes get about 4
            if publish:
                await logging.getLogger(COMPONENT_NAME).asyncLog("warn",
                                                                 "Sensor {!s} got no value".format(
                                                                     COMPONENT_NAME))
            return None
        return humid

    async def tempHumid(self, publish=True, timeout=5):
        temp = await self.temperature(publish=False)
        humid = await self.humidity(publish=False)
        if temp is None or humid is None:
            await logging.getLogger(COMPONENT_NAME).asyncLog("warn",
                                                             "Sensor {!s} got no value".format(
                                                                 COMPONENT_NAME))
        elif publish:
            await _mqtt.publish(self._topic, {
                "temperature": ("{0:." + str(self._prec_temp) + "f}").format(temp),
                "humidity":    ("{0:." + str(self._prec_humid) + "f}").format(humid)},
                                timeout=timeout, await_connection=False)
            # formating prevents values like 51.500000000001 on esp32_lobo
        return {"temperature": temp, "humiditiy": humid}
