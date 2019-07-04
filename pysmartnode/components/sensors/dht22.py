'''
Created on 2018-06-25

@author: Kevin Köck
'''

"""
example config:
{
    package: .sensors.dht22
    component: DHT22
    constructor_args: {
        pin: 4                    #pin number or label (on NodeMCU)
        precision_temp: 2         #precision of the temperature value published
        precision_humid: 1        #precision of the humid value published
        offset_temp: 0            #offset for temperature to compensate bad sensor reading offsets
        offset_humid: 0           #...             
        #interval: 600            #optional, defaults to 600
        #mqtt_topic: sometopic  #optional, defaults to home/<controller-id>/DHT22
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
"""

__updated__ = "2019-05-09"
__version__ = "0.4"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.component import Component, DISCOVERY_SENSOR
import gc

####################
# import your library here
from dht import DHT22 as Sensor

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
_component_name = "DHT22"
# define the type of the component according to the homeassistant specifications
_component_type = "sensor"
####################

_log = logging.getLogger(_component_name)
_mqtt = config.getMQTT()
gc.collect()

_count = 0


class DHT22(Component):
    def __init__(self, pin, precision_temp=2, precision_humid=1,  # extend or shrink according to your sensor
                 offset_temp=0, offset_humid=0,  # also here
                 interval=None, mqtt_topic=None, friendly_name=None):
        super().__init__()
        self._interval = interval or config.INTERVAL_SEND_SENSOR
        self._topic = mqtt_topic or _mqtt.getDeviceTopic(_component_name)

        ##############################
        # adapt to your sensor by extending/removing unneeded values like in the constructor arguments
        self._prec_temp = int(precision_temp)
        self._prec_humid = int(precision_humid)
        ###
        self._offs_temp = float(offset_temp)
        self._offs_humid = float(offset_humid)
        ##############################
        # create sensor object
        self.sensor = Sensor(Pin(pin))  # add neccessary constructor arguments here
        ##############################
        global _count
        self._count = _count
        _count += 1
        self._frn = friendly_name
        gc.collect()

    async def _init(self):
        await super()._init()
        gen = self.tempHumid
        interval = self._interval
        while True:
            await gen()
            await asyncio.sleep(interval)

    async def _dht_read(self):
        try:
            self.sensor.measure()
            await asyncio.sleep(1)
            self.sensor.measure()
        except Exception as e:
            await _log.asyncLog("error", "DHT22 is not working, {!s}".format(e))
            return None, None
        await asyncio.sleep_ms(100)  # give other tasks some time as measure() is slow and blocking
        try:
            temp = self.sensor.temperature()
            humid = self.sensor.humidity()
        except Exception as e:
            await _log.asyncLog("error", "Error reading DHT22: {!s}".format(e))
            return None, None
        return temp, humid

    async def _read(self, prec, offs, get_value_number=0, publish=True):
        if get_value_number > 2:
            _log.error("DHT22 get_value_number can't be >2")
            return None
        try:
            values = await self._dht_read()
        except Exception as e:
            await _log.asyncLog("error", "Error reading sensor {!s}: {!s}".format(_component_name, e))
            return None
        if values[0] is not None and values[1] is not None:
            for i in range(0, len(values)):
                try:
                    values[i] = round(values[i], prec)
                except Exception as e:
                    await _log.asyncLog("error", "DHT22 can't round value: {!s}, {!s}".format(values[i], e))
                    return None if get_value_number != 0 else (None, None)
                values[i] += offs
        else:
            await _log.asyncLog("warn", "Sensor {!s} got no value".format(_component_name))
            return None if get_value_number != 0 else (None, None)
        if publish:
            if get_value_number == 0:
                await _mqtt.publish(self._topic, {
                    "temperature": ("{0:." + str(self._prec_temp) + "f}").format(values[0]),
                    "humidity":    ("{0:." + str(self._prec_humid) + "f}").format(values[1])})
                # formating prevents values like 51.500000000001 on esp32_lobo
            else:
                await _mqtt.publish(self._topic, ("{0:." + str(prec) + "f}").format(values[get_value_number]))
        return {"temperature": values[0], "humiditiy": values[1]} if get_value_number == 0 else values[get_value_number]

    ##############################
    # remove or add functions below depending on the values of your sensor

    async def temperature(self, publish=True):
        return await self._read(self._prec_temp, self._offs_temp, 1, publish)

    async def humidity(self, publish=True):
        return await self._read(self._prec_humid, self._offs_humid, 2, publish)

    async def tempHumid(self, publish=True):
        return await self._read(self._prec_humid, self._offs_humid, 0, publish)

    ##############################

    async def _discovery(self):
        sens = DISCOVERY_SENSOR.format("temperature",  # device_class
                                       "°C",  # unit_of_measurement
                                       "{{ value|float }}")  # value_template
        name = "{!s}{!s}".format(_component_name, self._count)
        await self._publishDiscovery(_component_type, self._topic, name, sens, self._frn or "Temperature")
