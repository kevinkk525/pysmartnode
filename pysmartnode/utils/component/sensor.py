# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2019-10-27 

__updated__ = "2020-08-13"
__version__ = "0.9.2"

from pysmartnode.utils.component import ComponentBase
from pysmartnode import config
from .definitions import *
import uasyncio as asyncio
import gc
import time
import sys
import io
from micropython import const

try:
    import urandom as random
except:
    import random

# sensor value lookup table
_iPRECISION = const(0)
_iOFFSET = const(1)
_iVALUE_TEMPLATE = const(2)
_iUNIT_OF_MEAS = const(3)
_iFRIENDLY_NAME = const(4)
_iTOPIC = const(5)
_iDISC_TYPE = const(6)
_iBINARY_SENSOR = const(7)
_iUNIQUE_NAME = const(8)
_iTIMESTAMP = const(-2)
_iVALUE = const(-1)

_mqtt = config.getMQTT()


class ComponentSensor(ComponentBase):
    def __init__(self, component_name, version, unit_index: int, interval_publish=None,
                 interval_reading=None, mqtt_topic=None,
                 expose_intervals=False, intervals_topic=None,
                 publish_old_values=False, **kwargs):
        """
        :param component_name: Name of the component, used for default topics and logging
        :param version: version of the component module, used for logging purposes
        :param unit_index: counter of the registerd unit of this sensor_type (used for default topics)
        :param interval_publish: seconds, set to interval_reading to publish every reading. -1 for not publishing.
        :param interval_reading: seconds, set to -1 for not reading/publishing periodically. >0 possible for reading, 0 not allowed for reading..
        :param mqtt_topic: optional custom mqtt topic
        :param expose_intervals: Expose intervals to mqtt so they can be changed remotely
        :param intervals_topic: if expose_intervals then use this topic to change intervals.
        Defaults to <home>/<device-id>/<COMPONENT_NAME><_unit_index>/interval/set
        :param publish_old_values: Publish old values if the reading interval is higher than the publication can handle.
        Otherwise a publication is canceled and started again, which could result in a loop of never successful publication attempts if the read interval is high.
        """
        super().__init__(component_name, version, unit_index, **kwargs)
        self._values = {}
        # _intpb can be >0, -1 for not publishing or 0/None for config.INTERVAL_SENSOR_PUBLISH
        self._intpb: float = interval_publish or config.INTERVAL_SENSOR_PUBLISH
        self._intrd: float = config.INTERVAL_SENSOR_READ if interval_reading is None else interval_reading
        if self._intrd > self._intpb > 0:
            raise ValueError("interval_publish can't be lower than interval_reading")
        self._topic = mqtt_topic  # can be None
        self._event = None
        self._reading: bool = False  # cheaper than Lock
        if expose_intervals:
            tp = intervals_topic or _mqtt.getDeviceTopic(
                "{!s}/interval/set".format(self._default_name()))
            _mqtt.subscribeSync(tp, self.setInterval, self, qos=1, check_retained_state=True)
            self._log.info("Exposing intervals on topic", tp, local_only=True)
        self._loop_task = None
        if self._intrd > 0:  # if interval_reading==-1 no loop will be started
            self._loop_task = asyncio.create_task(self._loop())
            # self._loop_task will get canceled when component is removed.
        self._ignore_stale = publish_old_values
        gc.collect()

    async def _remove(self):
        """Called by component base class when a sensor component should be removed"""
        if self._loop_task is not None:
            self._loop_task.cancel()
        await super()._remove()

    def _addSensorType(self, sensor_type: str, precision: int = 0, offset: float = 0.0,
                       value_template: str = VALUE_TEMPLATE, unit_of_meas: str = "",
                       friendly_name: str = None, topic: str = None,
                       discovery_type: str = None, binary_sensor: bool = False,
                       unique_name: str = None):
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
        :param unique_name: Sensor name for discovery. Has to be unique. Optional, will get generated.
        :return:
        """
        self._values[sensor_type] = [int(precision), float(offset), value_template, unit_of_meas,
                                     friendly_name, topic, discovery_type, binary_sensor,
                                     unique_name, None, None]
        # value[-1] is last sensor reading, value[-2] is timestamp of last reading that is not None
        self._log.info("Sensor", self._default_name(), "will publish readings for", sensor_type,
                       "to topic", _mqtt.getRealTopic(
                topic or self._topic or _mqtt.getDeviceTopic(self._default_name())),
                       local_only=True)

    def setReadingInterval(self, *args):
        """
        Change the reading interval.
        Call function like setReadingInterval(5).
        Note that changing read interval to be bigger than publish interval will make
        publish interval behave like read interval.
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
        publish interval behave like read interval.
        :param args: args expected so function can be exposed to mqtt directly.
        :return:
        """
        self._intpb = float(args[0] if len(args) == 1 else args[1])
        return True

    def setInterval(self, *args):
        """
        Change both intervals using a dictionary. Can be exposed to mqtt
        :param args: {"reading":float,"publish":float}
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
        """
        Publish all current sensor readings.
        Ususally used internally but can be called externally to control the publication (e.g. if automatic publications are disabled).
        :param timeout: timeout for each publication operation
        :return:
        """
        d = {}
        t = self._topic or _mqtt.getDeviceTopic(self._default_name())
        for sensor_type in self._values:
            val = self._values[sensor_type]
            if val[_iVALUE] is not None:
                if val[_iTOPIC] is None:  # no topic for sensor_type
                    d[sensor_type] = val[_iVALUE]
                else:
                    msg = val[_iVALUE]
                    if type(msg) == bool and val[_iBINARY_SENSOR]:  # binary sensor
                        msg = _mqtt.payload_on[0] if msg else _mqtt.payload_off[0]
                    elif sys.platform in ("esp32", "pyboard") and type(msg) == float:
                        msg = ("{0:." + str(val[0]) + "f}").format(msg)
                        # on some platforms this might make sense as a workaround for 25.3000000001
                    await _mqtt.publish(val[_iTOPIC], msg, qos=1, timeout=timeout)
        if len(d) == 1 and "value_json" not in self._values[list(d.keys())[0]][_iVALUE_TEMPLATE]:
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
            if val[_iUNIQUE_NAME]:
                name = val[_iUNIQUE_NAME]
            elif len(self._values) > 0:
                name = "{!s}{!s}".format(self._default_name(), sensor_type[0].upper())
            else:
                name = self._default_name()
            expire = self._intpb * 2.1 if self._intpb > 0 else 0
            tp = val[_iDISC_TYPE] or self._composeSensorType(sensor_type, val[_iUNIT_OF_MEAS],
                                                             val[_iVALUE_TEMPLATE],
                                                             expire_after=expire,
                                                             binary=val[_iBINARY_SENSOR])
            if register:
                await self._publishDiscovery("binary_sensor" if val[_iBINARY_SENSOR] else "sensor",
                                             self.getTopic(sensor_type), name, tp,
                                             val[_iFRIENDLY_NAME] or "{}{}".format(
                                                 sensor_type[0].upper(), sensor_type[1:]))
            else:
                await self._deleteDiscovery("binary_sensor" if val[_iBINARY_SENSOR] else "sensor",
                                            name)
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

    async def getValues(self) -> dict:
        """Returns all current values as a dictionary. No read or publish possible"""
        return dict((x, self._values[x][_iVALUE]) for x in self._values)

    def getTimestamps(self) -> dict:
        return dict((x, self._values[x][_iTIMESTAMP]) for x in self._values)

    def getTimestamp(self, sensor_type) -> int:
        """Return timestamp of last successful sensor read (last value that was not None)"""
        self._checkType(sensor_type)
        return self._values[sensor_type][_iTIMESTAMP]

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
            if time.ticks_diff(time.ticks_ms(),
                               self._values[sensor_type][_iTIMESTAMP]) / 1000 > max_age:
                max_age = True
            else:
                max_age = False
        if max_age or self._intrd == -1:
            if self._reading:  # if currently reading, don't read again as value will be "live"
                while self._reading:
                    await asyncio.sleep_ms(20)
            else:
                self._reading = True
                await self._read()
                self._reading = False
            if publish:
                await self._publishValues(timeout=timeout)
        return self._values[sensor_type][_iVALUE]

    def getTemplate(self, sensor_type) -> str:
        self._checkType(sensor_type)
        return self._values[sensor_type][_iVALUE_TEMPLATE]

    def getTopic(self, sensor_type) -> str:
        self._checkType(sensor_type)
        return self._values[sensor_type][_iTOPIC] or self._topic or _mqtt.getDeviceTopic(
            self._default_name())

    async def _setValue(self, sensor_type, value, timeout=10, log_error=True):
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
                    value = round(value, s[_iPRECISION])
                    value += s[_iOFFSET]
                except Exception as e:
                    await self._log.asyncLog("error", "Error processing value:", e,
                                             timeout=timeout)
                    value = None
            elif type(value) not in (bool, str):
                await self._log.asyncLog("error", "Error processing value:", value,
                                         "no known type", timeout=timeout)
                value = None

        else:
            if log_error:
                await self._log.asyncLog("warn", "Got no value for", sensor_type, timeout=timeout)
        s[_iVALUE] = value
        if value:
            s[_iTIMESTAMP] = time.ticks_ms()  # time of last successful sensor reading

    async def _loop(self):
        await asyncio.sleep_ms(random.getrandbits(8) * 2)
        # delayed start to give network operations and discovery a chance.
        # also random between 0-2 seconds so not all components run at the same time.
        d = float("inf") if self._intpb == -1 else (self._intpb / self._intrd)
        i = d + 1  # so first reading gets published
        pub_task = None

        def pub(timeout=None):
            nonlocal pub_task
            await self._publishValues(timeout)
            pub_task = None

        try:
            while True:
                # d recalculated in loop so _intpb and _intrd can be changed during runtime
                d = float("inf") if self._intpb == -1 else (self._intpb / self._intrd)
                pb = i >= d
                i = 1 if pb else i + 1
                t = time.ticks_ms()
                while self._reading:
                    # wait when sensor is being read because of a getValue(max_age=...) request.
                    # getValue request could be called with publish=False so can't skip iteration.
                    await asyncio.sleep_ms(100)
                self._reading = True
                res = await self._read()
                self._reading = False
                if self._event and res is not False:
                    self._event.set()
                if pb and res is not False:
                    if pub_task and not self._ignore_stale:  # cancel active publish task
                        pub_task.cancel()
                        pub_task = None
                    # start a new publish task.
                    # Note: if reading interval is lower than publish nees,
                    # every publish gets canceled or causes OOM situation because the
                    # tasks can't get canceled quickly enough (waiing for socket lock).
                    # If self._ignore_stale the current value will be published even if new
                    # values are available due to higher reading interval.
                    if pub_task is None:
                        pub_task = asyncio.create_task(pub(5 if self._ignore_stale else None))
                # sleep until the sensor should be read again. Using loop with 500ms makes
                # changing the read interval during runtime possible with a reaction time of 500ms.
                hs = False
                while True:
                    sl = int(self._intrd * 1000 - time.ticks_diff(time.ticks_ms(), t))
                    sl = 500 if sl > 500 else sl if sl > 0 else 0
                    if sl == 0 and hs:  # sleeping done
                        break
                    # sleeping with 0 lets other coros run in between
                    await asyncio.sleep_ms(sl)
                    hs = True
        except asyncio.CancelledError:
            raise
        except NotImplementedError:
            raise
        except Exception as e:
            s = io.StringIO()
            sys.print_exception(e, s)
            await self._log.asyncLog("critical",
                                     "Exception in component loop: {!s}".format(s.getvalue()))
        finally:
            if pub_task is not None:
                pub_task.cancel()

    async def _read(self):
        """
        Subclass to read and store all sensor values.
        See sensor_template for examples of how to implement the _read method.
        :return:
        """
        raise NotImplementedError("No sensor _read method implemented")
