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
        #interval: 600            #optional, defaults to 600
        #mqtt_topic: sometopic  #optional, defaults to home/<controller-id>/HTU
    }
}
"""

__updated__ = "2018-08-31"
__version__ = "0.6"

from pysmartnode import config
from pysmartnode.utils.wrappers.async_wrapper import async_wrapper as _async_wrapper
from pysmartnode import logging
import uasyncio as asyncio
import gc

####################
# import your library here
from htu21d import HTU21D as Sensor

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
_component_name = "HTU"
####################

_log = logging.getLogger(_component_name)
_mqtt = config.getMQTT()
gc.collect()


class MySensor:
    def __init__(self, i2c, precision_temp=2, precision_humid=1,  # extend or shrink according to your sensor
                 offset_temp=0, offset_humid=0,  # also here
                 interval=None, mqtt_topic=None):
        interval = interval or config.INTERVAL_SEND_SENSOR
        self.topic = mqtt_topic or _mqtt.getDeviceTopic(_component_name)

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
            _log.error("Error reading sensor {!s}: {!s}".format(_component_name, e))
            return None
        if value is not None:
            value = round(value, prec)
            value += offs
        if value is None:
            _log.warn("Sensor {!s} got no value".format(_component_name))
        elif publish:
            await _mqtt.publish(self.topic, ("{0:." + str(prec) + "f}").format(value))
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
            await _mqtt.publish(self.topic, {
                "temperature": ("{0:." + str(self._prec_temp) + "f}").format(temp),
                "humidity": ("{0:." + str(self._prec_humid) + "f}").format(humid)})
            # formating prevents values like 51.500000000001 on esp32_lobo
        return {"temperature": temp, "humiditiy": humid}

    ##############################
