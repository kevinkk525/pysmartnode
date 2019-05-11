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
    }
}
"""

__version__ = "0.1"
__updated__ = "2018-08-18"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import gc
import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode.components.machine.adc import ADC
from pysmartnode.utils.component import Component, DISCOVERY_SENSOR
import time

_component_name = "Battery"
_component_type = "sensor"

_log = logging.getLogger(_component_name)
_mqtt = config.getMQTT()
gc.collect()


class Battery(Component):
    def __init__(self, adc, voltage_max, voltage_min, multiplier_adc, cutoff_pin=None,
                 precision_voltage=2, interval_watching=1,
                 interval=None, mqtt_topic=None, friendly_name=None):
        super().__init__()
        self._interval = interval or config.INTERVAL_SEND_SENSOR
        self._interval_watching = interval_watching
        self._topic = mqtt_topic or _mqtt.getDeviceTopic(_component_name)
        self._precision = int(precision_voltage)
        self._adc = ADC(adc)  # unified ADC interface
        self._voltage_max = voltage_max
        self._voltage_min = voltage_min
        self._multiplier = multiplier_adc
        self._cutoff_pin = None if cutoff_pin is None else (Pin(cutoff_pin, machine.Pin.OUT))
        if self._cutoff_pin is not None:
            self._cutoff_pin.value(0)
        self._frn = friendly_name
        gc.collect()
        self._event_low = None
        self._event_high = None

    def getVoltageMax(self):
        """Getter for consumers"""
        return self._voltage_max

    def getVoltageMin(self):
        """Getter for consumers"""
        return self._voltage_min

    async def _read(self, publish=True):
        try:
            value = self._adc.readVoltage()
        except Exception as e:
            _log.error("Error reading sensor {!s}: {!s}".format(_component_name, e))
            return None
        if value is not None:
            value *= self._multiplier
            value = round(value, self._precision)
        if value is None:
            _log.warn("Sensor {!s} got no value".format(_component_name))
        elif publish:
            await _mqtt.publish(self._topic, ("{0:." + str(self._precision) + "f}").format(value))
        return value

    async def voltage(self, publish=True):
        return await self._read(publish=publish)

    async def _init(self):
        await super()._init()
        interval = self._interval
        interval_watching = self._interval_watching
        t = time.ticks_ms()
        while True:
            if time.ticks_ms() > t:
                # publish interval
                voltage = self._read()
                t = time.ticks_ms() + interval
            else:
                voltage = self._read(publish=False)
            if voltage > self._voltage_max:
                if self._event_high is not None:
                    self._event_high.set(data=voltage)
                    # no log as consumer has to take care of logging or doing something
                else:
                    _log.warn("Battery voltage of {!s} exceeds maximum of {!s}".format(voltage, self._voltage_max))
            elif voltage < self._voltage_min:
                if self._event_low is not None:
                    self._event_low.set(data=voltage)
                    # no log as consumer has to take care of logging or doing something
                else:
                    _log.warn("Battery voltage of {!s} lower than minimum of {!s}".format(voltage, self._voltage_min))
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
                                       "{{ value|float }}")  # value_template
        await self._publishDiscovery(_component_type, self._topic, _component_name, sens, self._frn or "Battery")
