# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-10-26

"""
example config:
{
    package: .sensors.ds18
    component: DS18
    constructor_args: {
        pin: 5                    # pin number or label (on NodeMCU)
        # rom: 28FF016664160383"  # optional, ROM of the specific DS18 unit, can be string or bytearray (in json bytearray not possible). If not given then the first found ds18 unit will be used, no matter the ROM. Makes it possible to have a generic ds18 unit.
        # auto_detect: false      # optional, if true and ROM is None then all connected ds18 units will automatically generate a sensor object with the given options. If a sensor is removed, so will its object. Removed sensors will be removed from Homeassistant too!
        # interval_publish: 600   # optional, defaults to 600. Set to interval_reading to publish with every reading
        # interval_reading: 120   # optional, defaults to 120. -1 means do not automatically read sensor and publish
        # precision_temp: 2       # precision of the temperature value published
        # offset_temp: 0          # offset for temperature to compensate bad sensor reading offsets
        # mqtt_topic: sometopic   # optional, defaults to home/<device-id>/DS18
        # friendly_name: null     # optional, friendly name shown in homeassistant gui with mqtt discovery
        # discover: true          # optional, if false no discovery message for homeassistant will be sent
        # expose_intervals:       # optional, expose intervals to mqtt so they can be changed remotely
        # intervals_topic:        # optional, if expose_intervals then use this topic to change intervals. Defaults to <home>/<device-id>/<COMPONENT_NAME><_unit_index>/interval/set. Send a dictionary with keys "reading" and/or "publish" to change either/both intervals.
    }
}
# This module is to be used if only 1 ds18 sensor is connected and the ROM doesn't matter.
# It therefore provides a generic ds18 component for an exchangeable ds18 unit.
# The sensor can be replaced while the device is running.
"""

__updated__ = "2020-02-08"
__version__ = "3.1"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import gc
import time
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.component.sensor import ComponentSensor, SENSOR_TEMPERATURE, \
    VALUE_TEMPLATE_FLOAT

####################
# import your library here
import ds18x20
import onewire

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "DS18"
####################

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
_unit_index = -1
gc.collect()


class DS18(ComponentSensor):
    """
    Helping class to use a singluar DS18 unit.
    This is not a full component object in terms of mqtt and discovery. This is handled by the controller.
    It can be used as a temperature component object.
    """
    _pins = {}  # pin number/name:onewire()
    _last_conv = {}  # onewire:time
    _lock = asyncio.Lock()

    def __init__(self, pin, rom: str = None, auto_detect=False, interval_publish: float = None,
                 interval_reading: float = None, precision_temp: int = 2, offset_temp: float = 0,
                 mqtt_topic=None, friendly_name=None, discover=True, expose_intervals=False,
                 intervals_topic=None):
        """
        Class for a single ds18 unit to provide an interface to a single unit.
        :param pin: pin number/name/object
        :param rom: optional, ROM of the specific DS18 unit, can be string or bytearray
        (in json bytearray not possible). If not given then the first found ds18 unit will be used,
        no matter the ROM. Makes it possible to have a generic ds18 unit.
        :param auto_detect: optional, if true and ROM is None then all connected ds18 units will automatically generate a sensor object with the given options.
        :param interval_publish: seconds, set to interval_reading to publish every reading. -1 for not publishing.
        :param interval_reading: seconds, set to -1 for not reading/publishing periodically. >0 possible for reading, 0 not allowed for reading..
        :param precision_temp: the precision to for returning/publishing values
        :param offset_temp: temperature offset to adjust bad sensor readings
        :param mqtt_topic: optional mqtt topic of sensor
        :param friendly_name: friendly name in homeassistant
        :param discover: if DS18 object should send discovery message for homeassistnat
        :param expose_intervals: Expose intervals to mqtt so they can be changed remotely
        :param intervals_topic: if expose_intervals then use this topic to change intervals.
        Defaults to <home>/<device-id>/<COMPONENT_NAME><_unit_index>/interval/set
        Send a dictionary with keys "reading" and/or "publish" to change either/both intervals.
        """
        if rom is None and auto_detect:
            # only a dummy sensor for detecting connected sensors
            self._interval_reading = interval_reading
            self._interval_publishing = interval_publish
            interval_reading = 60  # scan every 60 seconds for new units
            interval_publish = -1
            self._instances = {}  # rom:object
            self._auto_detect = True
            self._prec = precision_temp
            self._offs = offset_temp
            self._discover = discover
            self._expose = expose_intervals
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, discover, interval_publish,
                         interval_reading, mqtt_topic, _log, expose_intervals, intervals_topic)
        if rom or not auto_detect:  # sensor with rom or generic sensor
            self._addSensorType(SENSOR_TEMPERATURE, precision_temp, offset_temp,
                                VALUE_TEMPLATE_FLOAT, "°C", friendly_name)
            self._auto_detect = False
        self._generic = True if rom is None and not auto_detect else False
        if type(pin) == ds18x20.DS18X20:
            self.sensor: ds18x20.DS18X20 = pin
        else:
            self._pins[pin] = ds18x20.DS18X20(onewire.OneWire(Pin(pin)))
            self.sensor: ds18x20.DS18X20 = self._pins[pin]
            self._last_conv[self.sensor] = None
        self.rom: str = rom
        gc.collect()

    def _default_name(self):
        """Change default name to include sensor ROM. Will change name and default topic."""
        if self.rom is None or self._generic:
            return "{!s}".format(COMPONENT_NAME)
        else:
            return "{!s}_{!s}".format(COMPONENT_NAME, self.rom)

    async def _read(self):
        if self._auto_detect or self._generic:  # auto_detect unit or generic sensor
            roms = []
            for _ in range(4):
                roms_n = self.sensor.scan()
                for rom in roms_n:
                    if rom not in roms:
                        roms.append(rom)
                await asyncio.sleep_ms(100)
            if len(roms) == 0:
                await _log.asyncLog("error", "Found no ds18 unit", timeout=10)
                return
            if self._auto_detect:  # auto_detect instance
                for rom in roms:
                    rom = self.rom2str(rom)
                    if rom not in self._instances:
                        self._instances[rom] = DS18(self.sensor, rom, False,
                                                    self._interval_publishing,
                                                    self._interval_reading, self._prec,
                                                    self._offs, None, None, self._discover,
                                                    self._expose)
                for rom in self._instances:
                    if rom not in roms:  # sensor not connected anymore
                        await self.removeComponent(roms[rom])
                        # will stop its loop and remove component and unsubcribe every topic
                        del self._instances[rom]
                        await _log.asyncLog("info", "DS18 removed:", rom, timeout=5)
            else:  # generic ds18 sensor
                rom = self.rom2str(roms[0])
                if rom != self.rom:  # sensor replaced
                    self.rom: str = rom
                    await _log.asyncLog("info", "Found new ds18:", rom, timeout=5)
        if self.rom is not None:  # DS18 sensor unit
            async with self._lock:
                if self._last_conv[self.sensor] is None or \
                        time.ticks_diff(time.ticks_ms(), self._last_conv[self.sensor]) > 5000:
                    # if sensors did convert time more than 5 seconds ago, convert temp again
                    self.sensor.convert_temp()
                    await asyncio.sleep_ms(750)
                value = None
                err = None
                for _ in range(3):
                    try:
                        value = self.sensor.read_temp(self.str2rom(self.rom))
                    except Exception as e:
                        await asyncio.sleep_ms(100)
                        err = e
                        continue
                if value is None:
                    await _log.asyncLog("error", "Sensor rom", self.rom, "got no value,", err,
                                        timeout=10)
                    return
                if value == 85.0:
                    await _log.asyncLog("error", "Sensor rom", self.rom,
                                        "got value 85.00 [not working correctly]", timeout=10)
                    return
                await self._setValue(SENSOR_TEMPERATURE, value)

    @staticmethod
    def rom2str(rom: bytearray) -> str:
        return ''.join('%02X' % i for i in iter(rom))

    @staticmethod
    def str2rom(rom: str) -> bytearray:
        a = bytearray(8)
        for i in range(8):
            a[i] = int(rom[i * 2:i * 2 + 2], 16)
        return a
