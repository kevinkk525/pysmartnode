# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
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
        # precision_temp: 2       # precision of the temperature value published
        # offset_temp: 0          # offset for temperature to compensate bad sensor reading offsets
        # friendly_name: null     # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
Every connected DS18 unit can be configured individually with this module.
However, this module can also be used if only 1 ds18 sensor is connected and the ROM doesn't matter.
Then it provides a generic ds18 component for an exchangeable ds18 unit. The sensor can be replaced while the device is running.
The module can also be used to automatically detect all connected DS18 units.
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

__updated__ = "2020-10-18"
__version__ = "3.6"

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
    _pins = {}  # pin number/name:onewire()
    _last_conv = {}  # onewire:time
    _lock = asyncio.Lock()

    def __init__(self, pin, rom: str = None, auto_detect=False, precision_temp: int = 2,
                 offset_temp: float = 0, friendly_name=None, **kwargs):
        """
        Class for a single ds18 unit to provide an interface to a single unit.
        Alternatively it can be used to automatically detect all connected units
        and create objects for those units.
        :param pin: pin number/name/object
        :param rom: optional, ROM of the specific DS18 unit, can be string or bytearray
        (in json bytearray not possible). If not given then the first found ds18 unit will be used,
        no matter the ROM. Makes it possible to have a generic ds18 unit.
        :param auto_detect: optional, if true and ROM is None then all connected ds18 units will automatically generate a sensor object with the given options.
        :param precision_temp: the precision to for returning/publishing values
        :param offset_temp: temperature offset to adjust bad sensor readings
        :param friendly_name: friendly name in homeassistant. Has no effect if rom is None and auto_detect True
        """
        if rom is None and auto_detect:
            # only a dummy sensor for detecting connected sensors
            interval_reading = kwargs["interval_reading"] if "interval_reading" in kwargs else None
            interval_publish = kwargs["interval_publish"] if "interval_publish" in kwargs else None
            self._instances = {}  # rom:object
            self._auto_detect = True
            self._kwargs = kwargs  # store kwargs for initialization of detected sensors
            kwargs["interval_reading"] = 60  # scan every 60 seconds for new units
            kwargs["interval_publish"] = -1
        global _unit_index
        _unit_index += 1
        self.rom: str = rom
        self._generic = True if rom is None and not auto_detect else False
        super().__init__(COMPONENT_NAME, __version__, _unit_index, logger=_log, **kwargs)
        if type(pin) == ds18x20.DS18X20:
            self.sensor: ds18x20.DS18X20 = pin
        else:
            self._pins[pin] = ds18x20.DS18X20(onewire.OneWire(Pin(pin)))
            self.sensor: ds18x20.DS18X20 = self._pins[pin]
            self._last_conv[self.sensor] = None
        if rom or not auto_detect:  # sensor with rom or generic sensor
            self._addSensorType(SENSOR_TEMPERATURE, precision_temp, offset_temp,
                                VALUE_TEMPLATE_FLOAT, "°C", friendly_name)
            self._auto_detect = False
        elif self._auto_detect:
            self._kwargs["interval_reading"] = interval_reading
            self._kwargs["interval_publish"] = interval_publish
            self._kwargs["precision_temp"] = precision_temp
            self._kwargs["offset_temp"] = offset_temp
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
                        self._instances[rom] = DS18(self.sensor, rom, False, **self._kwargs)
                for rom in self._instances:
                    if self.str2rom(rom) not in roms:  # sensor not connected anymore
                        await self.removeComponent(self._instances[rom])
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
                    try:
                        self.sensor.convert_temp()
                    except onewire.OneWireError:
                        await self._setValue(SENSOR_TEMPERATURE, None)
                        await _log.asyncLog("error", "Sensor rom", self.rom,
                                            ", onewire not connected?,", timeout=10)
                        return
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
                    await self._setValue(SENSOR_TEMPERATURE, None)
                    await _log.asyncLog("error", "Sensor rom", self.rom, "got no value,", err,
                                        timeout=10)
                    return
                if value == 85.0:
                    await self._setValue(SENSOR_TEMPERATURE, None)
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
