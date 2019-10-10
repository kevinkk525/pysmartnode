'''
Created on 2018-07-16

@author: Kevin Köck
'''

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
        # interval: 600     # optional, defaults to 600s, interval in which voltage gets published
        # mqtt_topic: null  # optional, defaults to <home>/<device-id>/battery
        # interval_watching: 1 # optional, the interval in which the voltage will be checked, defaults to 1s
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_abs: null # optional, friendly name for absolute voltage     
    }
}
WARNING: This component has not been tested with a battery and only works in theory!
"""

__version__ = "0.4"
__updated__ = "2019-10-10"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import gc
import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode.components.machine.adc import ADC
from pysmartnode.utils.component import Component, DISCOVERY_SENSOR
import time

COMPONENT_NAME = "Battery"
_COMPONENT_TYPE = "sensor"
_VAL_T_CHARGE = "{{ value_json.relative }}"
_VAL_T_VOLTAGE = "{{ value_json.absolute }}"

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_count = 0


class Battery(Component):
    def __init__(self, adc, voltage_max, voltage_min, multiplier_adc, cutoff_pin=None,
                 precision_voltage=2, interval_watching=1,
                 interval=None, mqtt_topic=None, friendly_name=None, friendly_name_abs=None):
        super().__init__(COMPONENT_NAME, __version__)
        self._interval = interval or config.INTERVAL_SEND_SENSOR
        self._interval_watching = interval_watching
        self._topic = mqtt_topic or _mqtt.getDeviceTopic(COMPONENT_NAME)
        self._precision = int(precision_voltage)
        self._adc = ADC(adc)  # unified ADC interface
        self._voltage_max = voltage_max
        self._voltage_min = voltage_min
        self._multiplier = multiplier_adc
        self._cutoff_pin = None if cutoff_pin is None else (Pin(cutoff_pin, machine.Pin.OUT))
        if self._cutoff_pin is not None:
            self._cutoff_pin.value(0)
        self._frn = friendly_name
        self._frn_abs = friendly_name_abs
        gc.collect()
        self._event_low = None
        self._event_high = None
        global _count
        self._count = _count
        _count += 1
        asyncio.get_event_loop().create_task(self._loop())

    def getVoltageMax(self):
        """Getter for consumers"""
        return self._voltage_max

    def getVoltageMin(self):
        """Getter for consumers"""
        return self._voltage_min

    async def _read(self, publish=True, timeout=5) -> tuple:
        try:
            value = self._adc.readVoltage()
        except Exception as e:
            _log.error("Error reading sensor {!s}: {!s}".format(COMPONENT_NAME, e))
            return None, None
        if value is not None:
            value *= self._multiplier
            value = round(value, self._precision)
        if value is None:
            _log.warn("Sensor {!s} got no value".format(COMPONENT_NAME))
            rela = None
        else:
            rela = (value - self._voltage_min) / (self._voltage_max - self._voltage_min)
        if publish and value is not None:
            await _mqtt.publish(self._topic, {
                "absolute": ("{0:." + str(self._precision) + "f}").format(value),
                "relative": ("{0:." + str(self._precision) + "f}").format(rela)},
                                timeout=timeout,
                                await_connection=False)
        return value, rela

    async def voltage(self, publish=True, timeout=5):
        return (await self._read(publish=publish, timeout=timeout))[0]

    async def charge(self, publish=True, timeout=5):
        return (await self._read(publish=publish, timeout=timeout))[1]

    @staticmethod
    def voltageTemplate():
        return _VAL_T_CHARGE

    async def _init(self):
        await super()._init()

    async def _loop(self):
        interval = self._interval
        interval_watching = self._interval_watching
        t = time.ticks_ms()
        while True:
            # reset events on next reading so consumers don't need to do it as there
            # might be multiple consumers awaiting
            if self._event_low is not None:
                self._event_low.release()
            if self._event_high is not None:
                self._event_high.release()
            if time.ticks_ms() > t:
                # publish interval
                voltage, charge = self._read()
                t = time.ticks_ms() + interval
            else:
                voltage, charge = self._read(publish=False)
            if voltage > self._voltage_max:
                if self._event_high is not None:
                    self._event_high.set(data=voltage)
                    # no log as consumer has to take care of logging or doing something
                else:
                    _log.warn("Battery voltage of {!s} exceeds maximum of {!s}".format(voltage,
                                                                                       self._voltage_max))
            elif voltage < self._voltage_min:
                if self._event_low is not None:
                    self._event_low.set(data=voltage)
                    # no log as consumer has to take care of logging or doing something
                else:
                    _log.warn("Battery voltage of {!s} lower than minimum of {!s}".format(voltage,
                                                                                          self._voltage_min))
                if self._cutoff_pin is not None:
                    if self._cutoff_pin.value() == 1:
                        _log.critical("Cutting off power did not work!")
                        self._cutoff_pin.value(0)  # trying again
                        await asyncio.sleep(1)
                    else:
                        _log.warn("Cutting off power")
                    await asyncio.sleep(5)  # time to send all logs and for consumers to get done
                    self._cutoff_pin.value(1)
            await asyncio.sleep(interval_watching)

    def registerEventHigh(self, event):
        self._event_high = event

    def registerEventLow(self, event):
        self._event_low = event

    async def _discovery(self):
        sens = DISCOVERY_SENSOR.format("battery",  # device_class
                                       "%",  # unit_of_measurement
                                       _VAL_T_CHARGE)  # value_template
        name = "{!s}{!s}{!s}".format(COMPONENT_NAME, self._count, "C")
        await self._publishDiscovery(_COMPONENT_TYPE, self._topic, name + "r", sens,
                                     self._frn or "Battery %")
        sens = '"unit_of_meas":"V",' \
               '"val_tpl":{!s},' \
               '"ic":"mdi:car-battery"'.format(_VAL_T_VOLTAGE)
        name = "{!s}{!s}{!s}".format(COMPONENT_NAME, self._count, "V")
        await self._publishDiscovery(_COMPONENT_TYPE, self._topic, name + "a", sens,
                                     self._frn_abs or "Battery Voltage")
        del sens
        gc.collect()
