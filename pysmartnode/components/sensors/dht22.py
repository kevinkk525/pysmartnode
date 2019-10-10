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

__updated__ = "2019-10-10"
__version__ = "0.6"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.component import Component
import gc

####################
# import your library here
from dht import DHT22 as Sensor

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "DHT22"
# define the type of the component according to the homeassistant specifications
_COMPONENT_TYPE = "sensor"
# define (homeassistant) value templates for all sensor readings
_VAL_T_TEMPERATURE = "{{ value_json.temperature }}"
_VAL_T_HUMIDITY = "{{ value_json.humidity }}"
####################

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_count = 0


class DHT22(Component):
    def __init__(self, pin, precision_temp=2, precision_humid=1,
                 # extend or shrink according to your sensor
                 offset_temp=0, offset_humid=0,  # also here
                 interval=None, mqtt_topic=None,
                 friendly_name_temp=None, friendly_name_humid=None):
        super().__init__(COMPONENT_NAME, __version__)
        self._interval = interval or config.INTERVAL_SEND_SENSOR
        self._topic = mqtt_topic or _mqtt.getDeviceTopic(COMPONENT_NAME)
        self._frn_temp = friendly_name_temp
        self._frn_humid = friendly_name_humid

        ##############################
        # adapt to your sensor by extending/removing unneeded values like in
        # the constructor arguments
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

    async def _read(self, publish=True, timeout=5):
        try:
            temp, humid = await self._dht_read()
        except Exception as e:
            await _log.asyncLog("error",
                                "Error reading sensor {!s}: {!s}".format(COMPONENT_NAME, e))
            return None, None
        if temp is not None:
            temp = round(temp, self._prec_temp)
            temp += self._offs_temp
        if temp is None:
            _log.warn("Sensor {!s} got no value".format(COMPONENT_NAME))
            # not making this await asyncLog as self.temperature is calling this
            # and might not want a network outage to block a sensor reading.
        if humid is not None:
            humid = round(humid, self._prec_humid)
            humid += self._offs_humid
        if humid is None:
            _log.warn("Sensor {!s} got no value".format(COMPONENT_NAME))
            # not making this await asyncLog as self.temperature is calling this
            # and might not want a network outage to block a sensor reading.
        if publish:
            await _mqtt.publish(self._topic, {
                "temperature": ("{0:." + str(self._prec_temp) + "f}").format(temp),
                "humidity":    ("{0:." + str(self._prec_humid) + "f}").format(humid)},
                                timeout=timeout, await_connection=False)
            # formating prevents values like 51.500000000001 on esp32_lobo
        return temp, humid

    ##############################
    # remove or add functions below depending on the values of your sensor

    async def temperature(self, publish=True, timeout=5):
        return (await self._read(publish, timeout))[0]

    async def humidity(self, publish=True, timeout=5):
        return (await self._read(publish, timeout))[1]

    async def tempHumid(self, publish=True, timeout=5) -> dict:
        temp, humid = await self._read(publish, timeout)
        return {"temperature": temp, "humiditiy": humid}

    @staticmethod
    def temperatureTemplate():
        """Other components like HVAC might need to know the value template of a sensor"""
        return _VAL_T_TEMPERATURE

    @staticmethod
    def humidityTemplate():
        """Other components like HVAC might need to know the value template of a sensor"""
        return _VAL_T_HUMIDITY

    ##############################

    async def _discovery(self):
        for v in (("T", "Temperature", "°C", "{{ value_json.temperature}}", self._frn_temp),
                  ("H", "Humidity", "%", "{{ value_json.humidity}}", self._frn_humid)):
            name = "{!s}{!s}{!s}".format(COMPONENT_NAME, self._count, v[0])
            sens = self._composeSensorType(v[1].lower(),  # device_class
                                           v[2],  # unit_of_measurement
                                           v[3])  # value_template
            await self._publishDiscovery(_COMPONENT_TYPE, self._topic, name, sens,
                                         v[4] or v[1])
            del name, sens
            gc.collect()
