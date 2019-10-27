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
        # interval: 600           # optional, defaults to 600. -1 means do not automatically read sensor and publish values
        # precision_temp: 2       # precision of the temperature value published
        # offset_temp: 0          # offset for temperature to compensate bad sensor reading offsets
        # mqtt_topic: sometopic   # optional, defaults to home/<device-id>/DS18
        # friendly_name: null     # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
# This module is to be used if only 1 ds18 sensor is connected and the ROM doesn't matter.
# It therefore provides a generic ds18 component for an exchangeable ds18 unit.
# The sensor can be replaced while the device is running.
"""

__updated__ = "2019-10-27"
__version__ = "1.1"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import gc
from pysmartnode.components.machine.pin import Pin
from pysmartnode.utils.component import Component

####################
# import your library here
import ds18x20
import onewire

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "DS18_S"
# define the type of the component according to the homeassistant specifications
_COMPONENT_TYPE = "sensor"
# define (homeassistant) value templates for all sensor readings
_VAL_T_TEMPERATURE = "{{ value|float }}"
####################

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()


class DS18(ds18x20.DS18X20, Component):
    """
    Helping class to use a singluar DS18 unit.
    This is not a full component object in terms of mqtt and discovery. This is handled by the controller.
    It can be used as a temperature component object.
    """

    def __init__(self, pin, interval=None, precision_temp=2, offset_temp=0, mqtt_topic=None,
                 friendly_name=None, discover=True):
        """
        Class for a single ds18 unit to provide an interface to a single unit.
        :param pin: pin number/name/object
        :param interval: interval to read the sensor
        :param precision_temp: the precision to for returning/publishing values
        :param offset_temp: temperature offset to adjust bad sensor readings
        :param mqtt_topic: optional mqtt topic of sensor
        :param friendly_name: friendly name in homeassistant
        :param discover: if DS18 object should send discovery message for homeassistnat
        """
        self._interval = interval or config.INTERVAL_SEND_SENSOR
        ds18x20.DS18X20.__init__(self, onewire.OneWire(Pin(pin)))
        Component.__init__(self, COMPONENT_NAME, __version__, discover=discover)
        self._topic = mqtt_topic  # can be None instead of default to save RAM
        self._frn = friendly_name
        gc.collect()
        self._lock = config.Lock()
        self.rom = None
        self.__temp = None
        if self._interval > 0:  # if interval==-1 no loop will be started
            asyncio.get_event_loop().create_task(self._loop())

        ##############################
        # adapt to your sensor by extending/removing unneeded values like in
        # the constructor arguments
        self._prec_temp = int(precision_temp)
        ###
        self._offs_temp = float(offset_temp)
        ##############################

    async def _loop(self):
        await asyncio.sleep(2)
        while True:
            interval = self._interval
            self.__temp = await self._read(publish=True)
            await asyncio.sleep(interval)

    async def _read(self, publish=True, timeout=5) -> float:
        async with self._lock:
            rom = None
            for _ in range(4):
                roms = self.scan()
                if len(roms) > 0:
                    rom = roms[0]
                    break
                await asyncio.sleep_ms(100)
            if rom is None:
                await _log.asyncLog("error", "Found no ds18 unit", timeout=20)
                return None
            if rom != self.rom:  # sensor replaced
                self.rom = rom
                await _log.asyncLog("info", "Found ds18: {!s}".format(self.rom2str(rom)),
                                    timeout=5)
            self.convert_temp()
            await asyncio.sleep_ms(750)
            value = None
            err = None
            for _ in range(3):
                try:
                    value = self.read_temp(rom)
                except Exception as e:
                    await asyncio.sleep_ms(100)
                    err = e
                    continue
            if value is None:
                await _log.asyncLog("error",
                                    "Sensor rom {!s} got no value, {!s}".format(self.rom2str(rom),
                                                                                err), timeout=20)
            if value is not None:
                if value == 85.0:
                    await _log.asyncLog("error",
                                        "Sensor rom {!s} got value 85.00 [not working correctly]".format(
                                            self.rom2str(rom)), timeout=20)
                    value = None
                try:
                    value = round(value, self._prec_temp)
                    value += self._offs_temp
                except Exception as e:
                    await _log.asyncLog("error",
                                        "Error rounding value {!s} of rom {!s}".format(value,
                                                                                       self.rom2str(
                                                                                           rom)),
                                        timeout=20)
                    value = None
            if publish:
                if value is not None:
                    topic = self._topic or _mqtt.getDeviceTopic("DS18")
                    await _mqtt.publish(topic,
                                        ("{0:." + str(self._prec_temp) + "f}").format(value),
                                        timeout=timeout, await_connection=False)
        return value

    @staticmethod
    def rom2str(rom: bytearray) -> str:
        return ''.join('%02X' % i for i in iter(rom))

    @staticmethod
    def str2rom(rom: str) -> bytearray:
        a = bytearray(8)
        for i in range(8):
            a[i] = int(rom[i * 2:i * 2 + 2], 16)
        return a

    async def _discovery(self):
        sens = self._composeSensorType("temperature",  # device_class
                                       "°C",  # unit_of_measurement
                                       _VAL_T_TEMPERATURE)  # value_template
        topic = self._topic or _mqtt.getDeviceTopic("DS18")
        await self._publishDiscovery(_COMPONENT_TYPE, topic, COMPONENT_NAME, sens,
                                     self._frn or "Temperature")
        del topic, sens
        gc.collect()

    def __str__(self):
        return "DS18"

    __repr__ = __str__

    async def temperature(self, publish=True, timeout=5, no_stale=False) -> float:
        """
        Read temperature of DS18 unit
        :param publish: bool, publish the read value
        :param timeout: int, for publishing
        :param no_stale: if True sensor will be read no matter loop activity or interval
        :return: float
        """
        if self._interval == -1 or no_stale:
            return await self._read(publish, timeout)
        else:
            return self.__temp

    @staticmethod
    def temperatureTemplate():
        """Other components like HVAC might need to know the value template of a sensor"""
        return _VAL_T_TEMPERATURE

    def temperatureTopic(self):
        return self._topic or _mqtt.getDeviceTopic("DS18")
