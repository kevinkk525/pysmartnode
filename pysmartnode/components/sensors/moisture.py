'''
Created on 20.04.2018

@author: Kevin Köck
'''

"""
example config:
{
    package: .sensors.moisture
    component: Moisture
    constructor_args: {
        adc_pin: 0             #pin number of ADC or name of amux component
        power_pin: [D5,5]      # can be a list to have one power_pin per sensor_type or single pin
        power_warmup: 100      #optional, time to wait before starting measurements (in ms) if a power_pin is used
        sensor_types: [0,1]          #optional, list of sensor types (if AMUX is used), 0: resistive, 1: capacitive, null: not connected
        water_voltage: [2.0, 1.5]   #value or list of voltage in  water per sensor_type, [0]=std, [1]=cap
        air_voltage: [0.0, 3.0]     #value or list of voltage in air per sensor_type
        publish_converted_value: true # optional, publish values "wet", "dry", "humid" additionally to percentage values
        # mqtt_topic: null           #optional, defaults to <home>/<device-id>/moisture/<#sensor>
        # interval: 600              #optional, interval of measurement
        # friendly_name: null       # optional, friendly name for the moisture sensor for homeassistant gui
        # friendly_name_cv: null    # optional, friendly name for the binary sensor publishing the converted vlaues (ON/OFF)
    }
}
"""

__updated__ = "2019-05-16"
__version__ = "1.0"

import machine
from pysmartnode.components.machine.pin import Pin
from pysmartnode.components.machine.adc import ADC, pyADC
from pysmartnode import config
import uasyncio as asyncio
import gc
from pysmartnode.utils.component import Component, DISCOVERY_SENSOR, DISCOVERY_BINARY_SENSOR

_component_name = "Moisture"
_component_type = "sensor"

_mqtt = config.getMQTT()
Lock = config.Lock
gc.collect()


# TODO: Divide sensor into multiple components as this is currently just a controller returning
#  all values and therefore doesn't conform to the new API. Only affects other programs calling humidity()

class Moisture(Component):
    def __init__(self, adc_pin, water_voltage, air_voltage, sensor_types,
                 power_pin=None, power_warmup=None,
                 publish_converted_value=False,
                 mqtt_topic=None, interval=None,
                 friendly_name=None, friendly_name_cv=None):
        super().__init__()
        self._adc = ADC(adc_pin)
        if power_pin is None:
            self._ppin = None
        else:
            if type(power_pin) == list:
                self._ppin = []
                for pin in power_pin:
                    self._ppin.append(Pin(pin, machine.Pin.OUT))
            else:
                self._ppin = Pin(power_pin, machine.Pin.OUT)
        self._power_warmup = power_warmup or None if power_pin is None else 10
        self._sensor_types = sensor_types
        if isinstance(self._adc, pyADC):  # pyADC provides unified single ADC interface, not AMUX
            raise TypeError("Single ADC (no Amux) can't have multiple sensors")
        self._water_v = water_voltage
        self._air_v = air_voltage
        if type(sensor_types) == list:
            if type(water_voltage) != list or type(air_voltage) != list:
                raise TypeError("Voltages have to be lists with multiple sensor_types")
        self._pub_cv = publish_converted_value
        self._topic = mqtt_topic or _mqtt.getDeviceTopic("moisture")
        self._interval = interval or config.INTERVAL_SEND_SENSOR
        self._lock = Lock()
        self._frn = friendly_name
        self._frn_cv = friendly_name_cv
        gc.collect()

    async def _init(self):
        await super()._init()
        while True:
            await self.humidity()
            await asyncio.sleep(self._interval)

    def _getConverted(self, sensor_type, voltage):
        if voltage is None:
            return None
        air_voltage = self._air_v if type(self._air_v) != list else self._air_v[sensor_type]
        water_voltage = self._water_v if type(self._water_v) != list else self._water_v[sensor_type]
        if sensor_type == 0:  # std sensor
            if voltage > (water_voltage - air_voltage) / 2 + air_voltage:
                return "ON"  # wet
            else:
                return "OFF"  # dry
        elif sensor_type == 1:  # capacitive
            if voltage > air_voltage - (air_voltage - water_voltage) / 2:
                return "OFF"  # dry
            else:
                return "ON"  # wet
        else:
            raise NotImplementedError("Sensor type {!s} not implemented".format(sensor_type))

    def _getPercentage(self, sensor_type, voltage):
        if voltage is None:
            return None
        air_voltage = self._air_v if type(self._air_v) != list else self._air_v[sensor_type]
        water_voltage = self._water_v if type(self._water_v) != list else self._water_v[sensor_type]
        if sensor_type == 0:  # std sensor:
            diff = water_voltage - air_voltage
            if voltage < air_voltage:
                return 0
            elif voltage > water_voltage:
                return 100
            return round((voltage - air_voltage) / diff * 100)
        elif sensor_type == 1:  # capacitive
            diff = air_voltage - water_voltage
            if voltage > air_voltage:
                return 0
            elif voltage < water_voltage:
                return 100
            return round((diff - (voltage - water_voltage)) / diff * 100)
        else:
            raise NotImplementedError("Sensor type {!s} not implemented".format(sensor_type))

    async def _read(self, publish=True) -> list:
        res = []
        i = 0
        amux = not isinstance(self._adc, pyADC)
        async with self._lock:
            if type(self._sensor_types) == list:
                sensors = self._sensor_types
            elif amux is True:
                sensors = [self._sensor_types] * self._adc.getSize()
            else:
                sensors = [self._sensor_types]
            for sensor in sensors:
                if self._ppin is not None:
                    if type(self._ppin) == list:
                        self._ppin[sensor].value(1)
                    else:
                        self._ppin.value(1)
                    await asyncio.sleep_ms(self._power_warmup)
                voltage = None
                if sensor is None:
                    res.append(None)
                else:
                    voltage = 0
                    for j in range(3):
                        voltage += self._adc.readVoltage(i) if amux else self._adc.readVoltage()
                    voltage /= 3
                    res.append(self._getPercentage(sensor, voltage))
                if publish:
                    await _mqtt.publish(self._topic + "/" + str(i), res[-1])
                    if self._pub_cv:
                        await _mqtt.publish(self._topic + "/" + str(i) + "/conv",
                                            self._getConverted(sensor, voltage))
                if self._ppin is not None:
                    if type(self._ppin) == list:
                        self._ppin[sensor].value(0)
                    else:
                        self._ppin.value(0)
                gc.collect()
                i += 1
        if len(res) == 0:
            return [None] * len(sensors)
        return res

    async def _discovery(self):
        amux = not isinstance(self._adc, pyADC)
        if type(self._sensor_types) == list:
            im = len(self._sensor_types)
        elif amux is True:
            im = self._adc.getSize()
        else:
            im = 1
        for i in range(im):
            if self._pub_cv:
                name = "{!s}{!s}CV".format(_component_name, i)
                sens = DISCOVERY_BINARY_SENSOR.format("moisture")  # device_class
                t = "{!s}/{!s}/conv".format(self._topic, i)
                await self._publishDiscovery("binary_sensor", t, name, sens, self._frn_cv or "Moisture")
            name = "{!s}{!s}".format(_component_name, i)
            t = "{!s}/{!s}".format(self._topic, i)
            sens = DISCOVERY_SENSOR.format("humidity",  # device_class
                                           "%",  # unit_of_measurement
                                           "{{ value|float }}")  # value_template
            await self._publishDiscovery(_component_type, t, name, sens, self._frn or "Moisture rel.")
            del name, sens, t
            gc.collect()

    async def humidity(self, publish=True) -> list:
        """
        Returns a list of all sensor values.
        Does currently not conform to new API definitions.
        """
        return await self._read(publish=publish)
