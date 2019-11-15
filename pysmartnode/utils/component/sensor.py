# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-10-27 

__updated__ = "2019-11-15"
__version__ = "0.6"

from pysmartnode.utils.component import Component
from pysmartnode import config
from pysmartnode import logging
from .definitions import *
import uasyncio as asyncio
import gc
import time

_mqtt = config.getMQTT()


class ComponentSensor(Component):
    def __init__(self, component_name, version, unit_index: int, discover, interval_publish=None,
                 interval_reading=None, mqtt_topic=None, log=None,
                 expose_intervals=False, intervals_topic=None):
        """
        :param component_name: Name of the component, used for default topics and logging
        :param version: version of the component module, used for logging purposes
        :param unit_index: counter of the registerd unit of this sensor_type (used for default topics)
        :param discover: if the sensor component should send its homeassistnat discovery message
        :param interval_publish: seconds, set to interval_reading to publish every reading. -1 for not publishing.
        :param interval_reading: seconds, set to -1 for not reading/publishing periodically. >0 possible for reading, 0 not allowed for reading..
        Be careful with relying on reading sensors quickly because every publish
        will take at most 5 seconds per sensor_type until it times out.
        If you rely on quick and reliable sensor reading times choose interval_publish=-1 and start
        your own coroutine for publishing values.
        :param mqtt_topic: optional custom mqtt topic
        :param expose_intervals: Expose intervals to mqtt so they can be changed remotely
        :param intervals_topic: if expose_intervals then use this topic to change intervals.
        Defaults to <home>/<device-id>/<COMPONENT_NAME><_unit_index>/interval/set
        """
        super().__init__(component_name, version, unit_index, discover)
        self._values = {}
        self._log = log or logging.getLogger(component_name)
        # _intpb can be >0, -1 for not publishing or 0/None for INTERVAL_SENSOR_PUBLISH
        self._intpb: float = interval_publish or config.INTERVAL_SENSOR_PUBLISH
        self._intrd: float = config.INTERVAL_SENSOR_READ if interval_reading is None else interval_reading
        if self._intpb < self._intrd:
            raise ValueError("interval_publish can't be lower than interval_reading")
        self._topic = mqtt_topic  # can be None
        self._event = None
        self._reading: bool = False  # cheaper than Lock
        if expose_intervals:
            _mqtt.subscribeSync(intervals_topic or _mqtt.getDeviceTopic(
                "{!s}/interval/set".format(self._default_name())),
                                self.setInterval, self, qos=1, check_retained_state=True)
        self._loop_task = None
        if self._intrd > 0:  # if interval_reading==-1 no loop will be started
            self._loop_task = asyncio.create_task(self._loop())
            # self._loop_task will get canceled when component is removed.
        gc.collect()

    async def _remove(self):
        """Called by component base class when a sensor component should be removed"""
        if self._loop_task is not None:
            self._loop_task.cancel()
        await super()._remove()

    def _addSensorType(self, sensor_type: str, precision: int, offset: float, value_template: str,
                       unit_of_meas: str, friendly_name: str = None, topic: str = None,
                       discovery_type: str = None, binary_sensor: bool = False):
        """
        :param sensor_type: Name of the sensor type, preferrably used by references to .definitons module
        :param precision: digits after separator "."
        :param offset: float offset to account for bad sensor readings
        :param value_template: value template in homeassistant.
        :param unit_of_meas: unit of measurement in homeassistant
        :param friendly_name: friendly name in homeassistant, falls back to sensor_type if not given
        :param topic: Each sensor_type can have its own topic or publish on one topic
        :param discovery_type: custom discovery configuration if sensor is not supported by
        standard types with device_class, unit_of_meas, value_template
        :param binary_sensor: if sensor is a binary_sensor, otherwise default sensor.
        :return:
        """
        tp = [int(precision), float(offset), value_template, unit_of_meas, friendly_name, topic,
              discovery_type, binary_sensor, None, None]
        # tp[-1] is last sensor reading, tp[-2] is timestamp of last reading (not None)
        self._values[sensor_type] = tp

    def setReadingInterval(self, *args):
        """
        Change the reading interval.
        Call function like setReadingInterval(5).
        Note that changing read interval to be bigger than publish interval will make
        publish interval to behave like read interval.
        :param args: args expected so function can be exposed to mqtt directly.
        :return:
        """
        self._intrd = float(args[0] if len(args) == 1 else args[1])
        return True

    def setPublishInterval(self, *args):
        """
        Change the publish interval.
        Call function like setReadingInterval(5).
        Note that changing publish interval to be smaller than read interval will make
        publish interval to behave like read interval.
        :param args: args expected so function can be exposed to mqtt directly.
        :return:
        """
        self._intpb = float(args[0] if len(args) == 1 else args[1])
        return True

    def setInterval(self, *args):
        """
        Change both intervals using a dictionary. Can be exposed to mqtt
        :param args:
        :return:
        """
        ints = args[0] if len(args) == 1 else args[1]
        if type(ints) != dict:
            raise TypeError("Interval change needs to be dict")
        if "reading" in ints:
            self.setReadingInterval(ints["reading"])
        if "publish" in ints:
            self.setPublishInterval(ints["publish"])
        return True

    def getReadingsEvent(self):
        """
        Returns an event that gets triggered on every read
        :return: Event
        """
        if self._event is None:
            self._event = asyncio.Event()
        return self._event

    async def _publishValues(self, timeout: float = 5):
        d = {}
        t = self._topic or _mqtt.getDeviceTopic(self._default_name())
        for sensor_type in self._values:
            val = self._values[sensor_type]
            if val[-1] is not None:
                if val[5] is None:  # no topic for sensor_type
                    d[sensor_type] = val[-1]
                else:
                    msg = val[-1]
                    if type(msg) == bool and val[7]:  # binary sensor
                        msg = _mqtt.payload_on[0] if msg else _mqtt.payload_off[0]
                    # elif type(msg)==float:
                    #     msg =("{0:." + str(val[0]) + "f}").format(msg)
                    # on some platforms this might make sense as a workaround for 25.3000000001
                    await _mqtt.publish(val[5], msg, qos=1, timeout=timeout)
        if len(d) == 1 and "value_json" not in self._values[list(d.keys())[0]][2]:
            # topic has no json template so send it without dict
            d = d[list(d.keys())[0]]
        if type(d) != dict or len(d) > 0:  # single value or dict with at least one entry
            await _mqtt.publish(t, d, qos=1, timeout=timeout)

    def _default_name(self):
        """
        Can be used to override the default naming pattern, e.g. if the sensors have a unique id
        """
        return "{!s}{!s}".format(self.COMPONENT_NAME, self._count)

    async def _discovery(self, register=True):
        for sensor_type in self._values:
            val = self._values[sensor_type]
            if len(self._values) > 0:
                name = "{!s}{!s}".format(self._default_name(), sensor_type[0].upper())
            else:
                name = self._default_name()
            tp = val[6] or self._composeSensorType(sensor_type, val[3], val[2])
            if register:
                await self._publishDiscovery("binary_sensor" if val[7] else "sensor",
                                             self.getTopic(sensor_type), name, tp,
                                             val[4] or "{}{}".format(sensor_type[0].upper(),
                                                                     sensor_type[1:]))
            else:
                await self._deleteDiscovery("binary_sensor", name)
            del name, tp
            gc.collect()

    @property
    def sensor_types(self):
        """
        Returns the registered sensor types so other components can check if the
        sensor object supports the type they want to read.
        """
        return self._values.keys()

    def _checkType(self, sensor_type):
        if sensor_type not in self._values:
            raise ValueError("sensor_type {!s} unknown".format(sensor_type))

    async def getValues(self):
        """Returns all current values as a dictionary. No read or publish possible"""
        return dict((x, self._values[x][-1]) for x in self._values)

    def getTimestamps(self):
        return dict((x, self._values[x][-2]) for x in self._values)

    def getTimestamp(self, sensor_type=None):
        """Return timestamp of last successful sensor read (last value that was not None)"""
        self._checkType(sensor_type)
        return self._values[sensor_type][-2]

    async def getValue(self, sensor_type, publish=True, timeout: float = 5, max_age: float = None):
        """
        Return last sensor reading of type "sensor_type".
        Only reads sensor if no loop is reading it periodically unless no_stale is True.
        If a loop is active, it will return the last read value which will be
        at most <self._intrd> old.
        Params publish and timeout will only have an effect if no loop is active or no_stale True.
        :param sensor_type: str representation of the sensor_type.
        :param publish: if value should be published if sensor has to be read for returned value
        :param timeout: timeout for publishing the value
        :param max_age: Specify how old the value can be. If it is older, the sensor will be read again.
        Makes long intervals possible with other components that rely on having a "live" sensor reading.
        :return: float or whatever the sensor_type has as a standard, None if no value available
        """
        self._checkType(sensor_type)
        if max_age:
            if time.ticks_diff(time.ticks_ms(), self._values[sensor_type][-2]) / 1000 > max_age:
                max_age = True
            else:
                max_age = False
        if max_age or self._intrd == -1:
            if self._reading:  # if currently reading, don't read again as value will be "live"
                while self._reading:
                    await asyncio.sleep_ms(100)
            else:
                self._reading = True
                await self._read()
                self._reading = False
            if publish:
                await self._publishValues(timeout=timeout)
        return self._values[sensor_type][-1]

    def getTemplate(self, sensor_type):
        self._checkType(sensor_type)
        return self._values[sensor_type][2]

    def getTopic(self, sensor_type):
        self._checkType(sensor_type)
        return self._values[sensor_type][5] or self._topic or _mqtt.getDeviceTopic(
            self._default_name())

    async def _setValue(self, sensor_type, value, timeout=10):
        """
        Set the newly read value for the given sensor_type
        :param sensor_type:
        :param value:
        :param timeout: timeout for logging if value is None or exception in processing value.
        If sensor is designed to be read quickly and logging if no value could be read is not
        relevant, then the sensor _read function should not call _setValue if it has no value.
        :return:
        """
        self._checkType(sensor_type)
        s = self._values[sensor_type]
        if value is not None:
            if type(value) in (int, float):
                try:
                    value = round(value, s[0])
                    value += s[1]
                except Exception as e:
                    log = self._log or logging.getLogger(self.COMPONENT_NAME)
                    await log.asyncLog("error", "Error processing value:", e, timeout=timeout)
                    value = None
            elif type(value) not in (bool, str):
                log = self._log or logging.getLogger(self.COMPONENT_NAME)
                await log.asyncLog("error", "Error processing value:", value, "no known type",
                                   timeout=timeout)
                value = None

        else:
            log = self._log or logging.getLogger(self.COMPONENT_NAME)
            await log.asyncLog("warn", "Got no value for", sensor_type, timeout=timeout)
        s[-1] = value
        if value:
            s[-2] = time.ticks_ms()

    async def _loop(self):
        await asyncio.sleep(1)
        d = float("inf") if self._intpb == -1 else (self._intpb / self._intrd)
        i = d + 1  # so first reading gets published
        pbc = None
        try:
            while True:
                # d recalculated in loop so _intpb and _intrd can be changed during runtime
                d = float("inf") if self._intpb == -1 else (self._intpb / self._intrd)
                pb = i >= d
                i = 1 if pb else i + 1
                t = time.ticks_ms()
                while self._reading:
                    # wait when sensor is read because of a getValue(no_stale=True) request
                    await asyncio.sleep_ms(50)
                self._reading = True
                await self._read()
                self._reading = False
                if self._event:
                    self._event.set()
                if pb:
                    if pbc is not None:
                        pbc.cancel()
                    vals = 0
                    # counting sensor_types which have a topic as those get published separately
                    for tp in self._values:
                        if tp[5] is not None:
                            vals += 1
                    vals = vals or 1  # if no type has a topic, one is still used to publish
                    sl = self._intrd * 1000 - time.ticks_diff(time.ticks_ms(), t)
                    if sl / 1000 > 5 * vals:
                        # if enough time is left until next reading then await publishing values
                        # (5 seconds per unique sensor_type)
                        await self._publishValues()
                    else:
                        # otherwise start task to publish values which might get canceled if
                        # it can't finish until next publish is requested.
                        pbc = asyncio.create_task(self._publishValues())
                # sleep until the sensor should be read again. Using loop with 100ms makes
                # changing the read interval during runtime possible with a reaction time of 100ms.
                while True:
                    sl = self._intrd * 1000 - time.ticks_diff(time.ticks_ms(), t)
                    sl = 100 if sl > 100 else sl if sl > 0 else 0
                    # sleeping with 0 lets other coros run in between
                    await asyncio.sleep_ms(sl)
                    if sl == 0:  # sleeping done
                        break
        except asyncio.CancelledError:
            if pbc is not None:
                pbc.cancel()
            raise
        except NotImplementedError:
            raise
        except Exception as e:
            if config.DEBUG:
                import sys
                sys.print_exception(e)
            await self._log.asyncLog("critical", "Exception in component loop:", e)

    async def _read(self):
        """
        Subclass to read and store all sensor values.
        See sensor_template for examples of how to implement the _read method.
        :return:
        """
        raise NotImplementedError("No sensor _read method implemented")
