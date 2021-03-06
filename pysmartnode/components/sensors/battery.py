# Author: Kevin Köck
# Copyright Kevin Köck 2018-2020 Released under the MIT license
# Created on 2018-07-16

"""
example config:
{
    package: .machine.battery
    component: Battery
    constructor_args: {
        adc: 0              # ADC pin number or ADC object (even Amux pin object)
        voltage_max: 14     # maximum voltage of the battery
        voltage_min: 10.5   # minimum voltage of the battery
        multiplier_adc: 2.5 # calculate the needed multiplier to get from the voltage read by adc to the real voltage
        cutoff_pin: null    # optional, pin number or object of a pin that will cut off the power if pin.value(1) 
        precision_voltage: 2 # optional, the precision of the voltage published by mqtt
        # interval_reading: 1 # optional, the interval in which the voltage will be checked, defaults to 1s
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_abs: null # optional, friendly name for absolute voltage
    }
}
WARNING: This component has not been tested with a battery and only works in theory!
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

__updated__ = "2020-03-29"
__version__ = "0.9"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import gc
import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode.components.machine.adc import ADC
from pysmartnode.utils.component.sensor import ComponentSensor, SENSOR_BATTERY

COMPONENT_NAME = "Battery"
_VAL_T_CHARGE = "{{ value_json.relative }}"
_VAL_T_VOLTAGE = "{{ value_json.absolute }}"
_TYPE_VOLTAGE = '"unit_of_meas":"V",' \
                '"val_tpl":{{ value_json.absolute }},' \
                '"ic":"mdi:car-battery"'

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_unit_index = -1


class Battery(ComponentSensor):
    def __init__(self, adc, voltage_max: float, voltage_min: float, multiplier_adc: float,
                 cutoff_pin=None, precision_voltage: int = 2, interval_reading: float = 1,
                 interval_publish: float = None, friendly_name: str = None,
                 friendly_name_abs: str = None, **kwargs):
        global _unit_index
        _unit_index += 1
        super().__init__(COMPONENT_NAME, __version__, _unit_index,
                         interval_publish=interval_publish, interval_reading=interval_reading,
                         logger=_log, **kwargs)
        self._adc = ADC(adc)  # unified ADC interface
        self._voltage_max = voltage_max
        self._voltage_min = voltage_min
        self._multiplier = multiplier_adc
        self._cutoff_pin = None if cutoff_pin is None else (Pin(cutoff_pin, machine.Pin.OUT))
        if self._cutoff_pin is not None:
            self._cutoff_pin.value(0)
        self._event_low = None
        self._event_high = None
        self._addSensorType(SENSOR_BATTERY, 2, 0, _VAL_T_CHARGE, "%", friendly_name_abs)
        self._addSensorType("voltage", precision_voltage, 0, _VAL_T_VOLTAGE, "V", friendly_name,
                            None, _TYPE_VOLTAGE)
        asyncio.create_task(self._events())
        gc.collect()

    def getVoltageMax(self) -> float:
        """Getter for consumers"""
        return self._voltage_max

    def getVoltageMin(self) -> float:
        """Getter for consumers"""
        return self._voltage_min

    async def _read(self):
        try:
            value = self._adc.readVoltage()
        except Exception as e:
            await _log.asyncLog("error", "Error reading sensor:", e, timeout=10)
        else:
            value *= self._multiplier
            await self._setValue("voltage", value)  # applies rounding and saves value
            value = await self.getValue("voltage")
            if value:
                value = (value - self._voltage_min) / (self._voltage_max - self._voltage_min)
                await self._setValue(SENSOR_BATTERY, value)

    async def _events(self):
        ev = self.getReadingsEvent()
        while True:
            # reset events on next reading so consumers don't need to do it as there
            # might be multiple consumers awaiting
            if self._event_low is not None:
                self._event_low.clear()
            if self._event_high is not None:
                self._event_high.clear()
            await ev.wait()
            voltage = await self.getValue("voltage")
            ev.clear()
            if voltage > self._voltage_max:
                if self._event_high is not None:
                    self._event_high.set()
                    # no log as consumer has to take care of logging or doing something
                else:
                    await _log.asyncLog("warn", "Battery voltage of", voltage,
                                        "exceeds maximum of",
                                        self._voltage_max, timeout=5)
            elif voltage < self._voltage_min:
                if self._event_low is not None:
                    self._event_low.set()
                    # no log as consumer has to take care of logging or doing something
                else:
                    await _log.asyncLog("warn", "Battery voltage of", voltage,
                                        "lower than minimum of", self._voltage_min, timeout=5)
                if self._cutoff_pin is not None:
                    if self._cutoff_pin.value() == 1:
                        await _log.asyncLog("critical", "Cutting off power did not work!",
                                            timeout=5)
                        self._cutoff_pin.value(0)  # trying again
                        await asyncio.sleep(1)
                    else:
                        await _log.asyncLog("warn", "Cutting off power", timeout=5)
                    await asyncio.sleep(5)  # time to send all logs and for consumers to get done
                    self._cutoff_pin.value(1)

    def registerEventHigh(self, event):
        self._event_high = event

    def registerEventLow(self, event):
        self._event_low = event
