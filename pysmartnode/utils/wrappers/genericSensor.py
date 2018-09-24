'''
Created on 14.04.2018

@author: Kevin Köck
'''

__updated__ = "2018-06-02"
__version__ = "0.3"

"""
Works but needs 1.5kB more RAM than the sensor_template
"""

from pysmartnode import config
from pysmartnode.utils.wrappers.async_wrapper import async_wrapper as _async_wrapper
import uasyncio as asyncio
import gc

_mqtt = config.getMQTT()


class SensorWrapper:
    def __init__(self, log, component_name,
                 interval=None, mqtt_topic=None,
                 retain=False, qos=0):
        self.interval = interval or config.INTERVAL_SEND_SENSOR
        self.component_name = component_name
        self.topic = mqtt_topic or _mqtt.getDeviceTopic(self.component_name)
        self.log = log
        self.retain = retain
        self.qos = qos

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
            await _mqtt.publish(self.topic, ("{0:." + str(prec) + "f}").format(value), self.retain, self.qos)
            # formating prevents values like 51.500000000001 on esp32_lobo
        return value

    def _startBackgroundLoop(self, background_loop):
        asyncio.get_event_loop().create_task(self._loop(background_loop, self.interval))

    def _registerMeasurement(self, func, precision, offset):
        try:
            func = _async_wrapper(func)
            precision = int(precision)
            offset = float(offset)
        except Exception as e:
            self.log.error("Error registering measurement: {!s}".format(e))
        gc.collect()

        async def reading(publish=True):
            return await self._read(func, precision, offset, publish)

        return reading
