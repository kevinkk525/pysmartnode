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
        i2c: i2c                   #i2c object created before
        precision_temp: 2         #precision of the temperature value published
        precision_humid: 1        #precision of the humid value published
        temp_offset: 0            #offset for temperature to compensate bad sensor reading offsets
        humid_offset: 0           #...             
        #interval: 600            #optional, defaults to 600
        #mqtt_topic: sometopic  #optional, defaults to home/<controller-id>/HTU
    }
}
"""

__updated__ = "2018-08-31"
__version__ = "0.8"

import gc
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.libraries.htu21d.htu21d_async import HTU21D as htu
import uasyncio as asyncio

_component_name = "HTU"

_mqtt = config.getMQTT()
gc.collect()


class HTU21D(htu):
    def __init__(self, i2c, precision_temp, precision_humid,
                 temp_offset, humid_offset,
                 mqtt_topic=None, interval=None):
        interval = interval or config.INTERVAL_SEND_SENSOR
        self.topic = mqtt_topic or _mqtt.getDeviceTopic(_component_name)
        ##############################
        # adapt to your sensor by extending/removing unneeded values
        self._prec_temp = int(precision_temp)
        self._prec_humid = int(precision_humid)
        ###
        self._offs_temp = float(temp_offset)
        self._offs_humid = float(humid_offset)
        ##############################
        # create sensor object
        super().__init__(i2c=i2c)
        ##############################
        # create a link to the functions of the sensor
        # (if that function is a coroutine you can omit _async_wrapper)
        self._temp = self.temperature_async
        self._humid = self.humidity_async
        ##############################
        # choose a background loop that periodically reads the values and publishes it
        # (function is created below)
        background_loop = self.tempHumid
        ##############################

        gc.collect()
        asyncio.get_event_loop().create_task(self._loop(background_loop, interval))

    async def _loop(self, gen, interval):
        while True:
            await gen()
            await asyncio.sleep(interval)

    async def _read(self, coro, prec, offs, publish=True):
        if coro is None:
            raise TypeError("Sensor generator is of type None")
        try:
            value = await coro()
        except Exception as e:
            logging.getLogger(_component_name).error("Error reading sensor {!s}: {!s}".format(_component_name, e))
            return None
        if value is not None:
            value = round(value, prec)
            value += offs
        if value is None:
            logging.getLogger(_component_name).warn("Sensor {!s} got no value".format(_component_name))
        elif publish:
            await _mqtt.publish(self.topic, ("{0:." + str(prec) + "f}").format(value))
        return value

    async def temperature(self, publish=True):
        return await self._read(self._temp, self._prec_temp, self._offs_temp, publish)

    async def humidity(self, publish=True):
        return await self._read(self._humid, self._prec_humid, self._offs_humid, publish)

    async def tempHumid(self, publish=True):
        temp = await self.temperature(publish=False)
        humid = await self.humidity(publish=False)
        if temp is not None and humid is not None and publish:
            await _mqtt.publish(self.topic, {
                "temperature": ("{0:." + str(self._prec_temp) + "f}").format(temp),
                "humidity": ("{0:." + str(self._prec_humid) + "f}").format(humid)})
            # formating prevents values like 51.500000000001 on esp32_lobo
        return {"temperature": temp, "humiditiy": humid}
