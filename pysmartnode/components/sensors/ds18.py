'''
Created on 2018-06-25

@author: Kevin Köck
'''

"""
example config:
# DS18 general controller:
{
    package: .sensors.ds18
    component: DS18
    constructor_args: {
        pin: 5                    # pin number or label (on NodeMCU)
        precision_temp: 2         #precision of the temperature value published
        offset_temp: 0            #offset for temperature to compensate bad sensor reading offsets
        #interval: 600            #optional, defaults to 600
        #mqtt_topic: sometopic  #optional, defaults to home/<controller-id>/DS18, multiple sensor to /DS18/rom
    }
}

# Specific DS18 unit to get temperature from this unit without specifying the rom on temperature request
{
    package: .sensors.ds18
    component: DS18_Unit
    constructor_args: {
        rom: "28FF016664160383"   # ROM of the specific DS18 unit, can be string or bytearray (in json bytearray not possible)
        # controller: "ds18"      # optional, name of controller instance. Not needed if only one instance created) 
    }
}
"""

__updated__ = "2019-04-21"
__version__ = "1.1"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import gc
from pysmartnode.components.machine.pin import Pin

####################
# import your library here
import ds18x20
import onewire

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
_component_name = "DS18"
####################

_log = logging.getLogger(_component_name)
_mqtt = config.getMQTT()
gc.collect()

_ds18_controller = None


class DS18(ds18x20.DS18X20):
    def __init__(self, pin, precision_temp=2, offset_temp=0,
                 interval=None, mqtt_topic=None):
        interval = interval or config.INTERVAL_SEND_SENSOR
        self.topic = mqtt_topic or _mqtt.getDeviceTopic(_component_name)

        ##############################
        # adapt to your sensor by extending/removing unneeded values like in the constructor arguments
        self._prec_temp = int(precision_temp)
        ###
        self._offs_temp = float(offset_temp)
        ##############################
        # create sensor object
        super().__init__(onewire.OneWire(Pin(pin)))
        ##############################
        # choose a background loop that periodically reads the values and publishes it
        # (function is created below)
        background_loop = self.temperature
        ##############################
        gc.collect()
        asyncio.get_event_loop().create_task(self._loop(background_loop, interval))
        global _ds18_controller
        _ds18_controller = self

    @staticmethod
    async def _loop(gen, interval):
        await asyncio.sleep(1)
        while True:
            await gen()
            await asyncio.sleep(interval)

    async def _read(self, prec, offs, publish=True) -> (list, list):
        roms = []
        for _ in range(3):
            roms = self.scan()
            if len(roms) > 0:
                break
            await asyncio.sleep_ms(100)
        if len(roms) == 0:
            await _log.asyncLog("error", "No DS18 found")
            return None, []
        self.convert_temp()
        await asyncio.sleep_ms(750)
        values = []
        for rom in roms:
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
                                    "Sensor {!s}, rom {!s} got no value, {!s}".format(_component_name, rom, err))
            values.append(value)
            if values[-1] is not None:
                if values[-1] == 85.0:
                    await _log.asyncLog("error", "Sensor {!s}, rom {!s} got value 85.00 [not working correctly]".format(
                        _component_name, rom))
                    values[-1] = None
                    continue
                try:
                    values[-1] = round(values[-1], prec)
                    values[-1] += offs
                except Exception as e:
                    await _log.asyncLog("error", "Error rounding value {!s} of rom {!s}".format(values[-1], rom))
                    values[-1] = None
        if publish:
            if len(values) == 1:
                await _mqtt.publish(self.topic, ("{0:." + str(prec) + "f}").format(values[0]))
            for i in range(0, len(values)):
                if values[i] is not None:
                    await _mqtt.publish("{!s}/{!s}".format(self.topic, self.rom2str(roms[i])),
                                        ("{0:." + str(prec) + "f}").format(values[i]))
        return values, roms

    ##############################
    # remove or add functions below depending on the values of your sensor

    async def temperature(self, rom: bytearray = None, return_roms: bool = False, publish=True) -> float:
        """sensor_number: number of sensor in roms, None for all values"""
        values, roms = await self._read(self._prec_temp, self._offs_temp, publish)
        if rom is not None:
            if rom in roms:
                return values[roms.index(rom)]
            else:
                return None
        if return_roms is True:
            return values, roms
        # return first temperature to not break compatibility to sensor API
        return values[0] if values is not None else None

    ##############################

    @staticmethod
    def rom2str(rom: bytearray) -> str:
        return ''.join('%02X' % i for i in iter(rom))

    @staticmethod
    def str2rom(rom: str) -> bytearray:
        a = bytearray(8)
        for i in range(8):
            a[i] = int(rom[i * 2:i * 2 + 2], 16)
        return a


class DS18_Unit:
    def __init__(self, rom, controller: DS18 = None):
        """
        Class for a single ds18 unit to provide an interface to a single unit not needing to specify
        the ROM on temperature read calls.
        :param rom: str or bytearray, device specific ROM
        :param controller: DS18 object. If ds18 are connected on different pins, different DS18 objects are needed
        """
        if controller is None:
            global _ds18_controller
            if _ds18_controller is None:
                raise TypeError("No DS18 object, create the onewire ds18 controller instance first")
            self._ds = _ds18_controller
        else:
            self._ds = controller
        self._r = rom if type(rom) == bytearray else self._ds.str2rom(rom)

    def __str__(self):
        return "DS18({!s})".format(self._ds.rom2str(self._r))

    __repr__ = __str__

    async def temperature(self, publish=True):
        """
        Will read all ds18 sensors but return only the temperature of this sensor.
        :param publish: if all readings should be publish.
        :return: float, None on error
        """
        return await self._ds.temperature(self._r, publish=publish)
