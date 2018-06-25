'''
Created on 14.04.2018

@author: Kevin Köck
'''

__updated__ = "2018-05-20"
__version__ = "0.4"

"""
This module wraps around every sensor that has a temperature and/or humidity function or coroutine
(properties are not supported).
You can use this module on the esp8266 but only if you use nothing else as it consumes a lot of RAM

example config:
{
    package: .sensors.tempHumidWrapper
    component: sensor
    constructor_args: {
        package: pysmartnode.libraries.htu21d_async
        component: HTU21D
        constructor_args: {       # is being looked up in config.COMPONENTS for registered components
            scl:null
            sda:null
        }
        temp_function: temperature_async
        humid_function: humidity_async      # or null if not available for sensor
        init_function: null
        init_args: null
        component_name: htu       #optional, defaults to sensor_component; name saved in config.COMPONENTS but also used as mqtt_topic if not provided
        mqtt_topic: sometopic     #optional, defaults to home/<controller-id>/<sensor_component>
        interval: 600             #optional, defaults to 600
        precision_temp: 2         #optional, precision of the temperature value published
        precision_humid: 1        #optional, precision of the humid value published
        temp_offset: 0            #optional, offset for temperature to compensate bad sensor reading offsets
        humid_offset: 0           #optional, ...      
    }
}
"""

from pysmartnode import config

mqtt = config.getMQTT()
from pysmartnode import logging
import uasyncio as asyncio
import gc

gc.collect()


def sensor(package, component, constructor_args=None, temp_function=None, humid_function=None,
           init_function=None, init_args=None, sensor_component_name=None,
           mqtt_topic=None, interval=None,
           precision_temp=2, precision_humid=1, temp_offset=0, humid_offset=0):
    sensor_component_name = sensor_component_name or component
    log = logging.getLogger(sensor_component_name)
    conf = {"_order": [sensor_component_name],
            sensor_component_name: {"package": package, "component": component,
                                    "constructor_args": constructor_args,
                                    "init_function": init_function, "init_args": init_args}}
    if config.registerComponents(conf) == False:
        log.critical("Can't wrap component {!s} as sensor registration failed".format(
            sensor_component_name))
        return False
    gc.collect()
    del conf
    gc.collect()
    component = config.getComponent(sensor_component_name)
    if component is None:
        log.critical("Can't wrap component {!s} as sensor does not exist in config.COMPONENTS".format(
            sensor_component_name))
        return False
    for f in [temp_function, humid_function]:
        if f is not None and hasattr(component, f) == False:
            log.critical("Sensor {!s} has no function {!s}, can't register".format(
                sensor_component_name, f))
            return False
    interval = interval or config.INTERVAL_SEND_SENSOR
    mqtt_topic = mqtt_topic or mqtt.getDeviceTopic(sensor_component_name)
    return SensorWrapper(sensor_component_name, component, temp_function, humid_function,
                         mqtt_topic, interval, precision_temp, precision_humid, temp_offset,
                         humid_offset)


def _async_wrapper(f):
    """ property not supported, only function and coroutine """

    async def wrap():
        res = f()
        if str(type(res)) == "<class 'generator'>":
            res = await res
        return res

    return wrap


class SensorWrapper:
    def __init__(self, component_name, component, temp_function, humid_function, mqtt_topic,
                 interval, precision_temp, precision_humid, temp_offset, humid_offset):
        self.sensor = component
        gen = None
        if temp_function is not None:
            self._temp = _async_wrapper(getattr(component, temp_function))
            self._prec_temp = int(precision_temp)
            self._offs_temp = float(temp_offset)
            self.temperature = self.__temperature
            gen = self.temperature
        if humid_function is not None:
            self._humid = _async_wrapper(getattr(component, humid_function))
            self._prec_humid = int(precision_humid)
            self._offs_humid = float(humid_offset)
            self.humidity = self.__humidity
            gen = self.humidity
        if temp_function is not None and humid_function is not None:
            self.tempHumid = self.__tempHumid
            gen = self.tempHumid
        self.topic = mqtt_topic or mqtt.getDeviceTopic(component_name)
        self.log = logging.getLogger(component_name)
        self.component_name = component_name
        asyncio.get_event_loop().create_task(self._loop(gen, interval))

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
            self.log.error("Error reading sensor {!s}: {!s}".format(self.component_name, e))
            return None
        if value is not None:
            value = round(value, prec)
            value += offs
        if value is None:
            self.log.warn("Sensor {!s} got no value".format(self.component_name))
        elif publish:
            await mqtt.publish(self.topic, value)
        return value

    async def __temperature(self, publish=True):
        return await self._read(self._temp, self._prec_temp, self._offs_temp, publish)

    async def __humidity(self, publish=True):
        return await self._read(self._humid, self._prec_humid, self._offs_humid, publish)

    async def __tempHumid(self, publish=True):
        temp = await self.temperature(publish=False)
        humid = await self.humidity(publish=False)
        if temp is not None and humid is not None and publish:
            await mqtt.publish(self.topic, {"temperature": temp, "humidity": humid})
        return {"temperature": temp, "humiditiy": humid}
