# Author: Kevin Köck
# Copyright Kevin Köck 2017-2020 Released under the MIT license
# Created on 2017-10-28

"""
example config:
{
    package: .sensors.htu21d
    component: HTU21D
    constructor_args: {
        i2c: i2c                    # i2c object created before
        precision_temp: 2           # precision of the temperature value published
        precision_humid: 1          # precision of the humid value published
        temp_offset: 0              # offset for temperature to compensate bad sensor reading offsets
        humid_offset: 0             # ...
        # friendly_name_temp: null  # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_humid: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

__updated__ = "2020-03-29"
__version__ = "3.2"

import gc
import uasyncio as asyncio
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.component.sensor import ComponentSensor, SENSOR_TEMPERATURE, SENSOR_HUMIDITY

####################
# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "HTU"
# define (homeassistant) value templates for all sensor readings
_VAL_T_TEMPERATURE = "{{ value_json.temperature }}"
_VAL_T_HUMIDITY = "{{ value_json.humidity }}"
####################

_mqtt = config.getMQTT()
_log = logging.getLogger(COMPONENT_NAME)
gc.collect()

_unit_index = -1
_ADDRESS = 0x40
_ISSUE_TEMP_ADDRESS = 0xE3
_ISSUE_HU_ADDRESS = 0xE5


class HTU21D(ComponentSensor):
    def __init__(self, i2c, precision_temp: int = 2, precision_humid: int = 2,
                 temp_offset: float = 0, humid_offset: float = 0,
                 friendly_name_temp=None, friendly_name_humid=None, **kwargs):
        # This makes it possible to use multiple instances of MySensor and have unique identifier
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index, logger=_log, **kwargs)
        # discover: boolean, if this component should publish its mqtt discovery.
        # This can be used to prevent combined Components from exposing underlying
        # hardware components like a power switch
        self.i2c = i2c
        self._addSensorType(SENSOR_TEMPERATURE, precision_temp, temp_offset, _VAL_T_TEMPERATURE,
                            "°C", friendly_name_temp)
        self._addSensorType(SENSOR_HUMIDITY, precision_humid, humid_offset, _VAL_T_HUMIDITY, "%",
                            friendly_name_humid)

        gc.collect()
        ##############################

    async def _read(self):
        raw = await self._issue_measurement_async(_ISSUE_TEMP_ADDRESS)
        if raw is not None:
            await self._setValue(SENSOR_TEMPERATURE, -46.85 + (175.72 * raw / 65536))
            raw = await self._issue_measurement_async(_ISSUE_HU_ADDRESS)
            if raw is not None:
                await self._setValue(SENSOR_HUMIDITY, -6 + (125.0 * raw / 65536))

    async def _issue_measurement_async(self, write_address):
        try:
            # self.i2c.start()
            self.i2c.writeto_mem(int(_ADDRESS), int(write_address), '')
            # self.i2c.stop()
            data = bytearray(3)
        except Exception as e:
            await self._log.asyncLog("error", "Error reading sensor:", e, timeout=10)
            return None
        await asyncio.sleep_ms(50)
        try:
            self.i2c.readfrom_into(_ADDRESS, data)
            remainder = ((data[0] << 8) + data[1]) << 8
            remainder |= data[2]
            divsor = 0x988000
            for i in range(0, 16):
                if remainder & 1 << (23 - i):
                    remainder ^= divsor
                divsor >>= 1
            if remainder:
                await self._log.asyncLog("error", "Checksum error", timeout=10)
                return None
            raw = (data[0] << 8) + data[1]
            raw &= 0xFFFC
            return raw
        except Exception as e:
            await self._log.asyncLog("error", "Error reading sensor:", e, timeout=10)
            return None
