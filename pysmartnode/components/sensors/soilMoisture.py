'''
Created on 20.04.2018

@author: Kevin Köck
'''

"""
example config:
{
    package: .sensors.soilMoisture
    component: SoilMoisture
    constructor_args: {
        adc_pin: 0             #pin number of ADC or name of amux component
        power_pin: [D5,5]      # can be a list to have one power_pin per sensor_type or single pin
        power_warmup: 100      #optional, time to wait before starting measurements (in ms) if a power_pin is used
        sensor_types: [0,1]          #optional, list of sensor types (if AMUX is used), 0: resistive, 1: capacitive, null: not connected
        water_voltage: [2.0, 1.5]   #value or list of voltage in  water per sensor_type, [0]=std, [1]=cap
        air_voltage: [0.0, 3.0]     #value or list of voltage in air per sensor_type
        publish_converted_value: true # optional, publish values "wet", "dry", "humid" additionally to percentage values         mqtt_topic: sometopic,     #optional
        #mqtt_topic: null           #optional, defaults to <home>/<device-id>/soilMoisture/<#sensor>
        #interval: 600              #optional, interval of measurement
    }
}
"""

__updated__ = "2018-05-20"
__version__ = "0.7"

from machine import Pin, ADC
from pysmartnode import config
from sys import platform
import uasyncio as asyncio
import gc
from pysmartnode import logging

log = logging.getLogger("soil")
mqtt = config.getMQTT()
Lock = config.Lock


class SoilMoisture:
    def __init__(self, adc_pin, water_voltage, air_voltage, sensor_types,
                 power_pin=None, power_warmup=None,
                 publish_converted_value=False,
                 mqtt_topic=None, interval=None):
        if platform == "esp8266":
            if type(adc_pin) == int:
                self.adc = ADC(0)

                def read_voltage():
                    return self.adc.read() / 1024 * 3.3

                self._adc_read = read_voltage
            else:
                # AMUX
                self.adc = adc_pin
                self._adc_read = self.adc.read
        elif platform == "esp32_LoBo":
            self.adc = ADC(adc_pin) if type(adc_pin) == int else adc_pin
            self._adc_read = self.adc.read
            if type(adc_pin) == int:
                self.adc.atten(self.adc.ATTN_11DB)
            else:
                # set AMUX to return Voltages
                self.adc.setReturnVoltages(True)
        else:
            raise NotImplementedError("Platform {!s} not implemented, please report".format(platform))
            # self.adc=ADC(Pin(adc_pin))
        if power_pin is None:
            self.power_pin = None
        else:
            if type(power_pin) == list:
                self.power_pin = []
                for pin in power_pin:
                    self.power_pin.append(Pin(pin if type(pin) == int else config.pins[pin], Pin.OUT))
            else:
                self.power_pin = Pin(power_pin if type(power_pin) == int else config.pins[power_pin], Pin.OUT)
        self.power_warmup = power_warmup or None if power_pin is None else 10
        self.sensor_types = sensor_types
        if type(sensor_types) == list and type(self.adc) == ADC:
            raise TypeError("Single ADC (no Amux) can't have multiple sensor_types")
        self.water_voltage = water_voltage
        self.air_voltage = air_voltage
        if type(sensor_types) == list:
            if type(water_voltage) != list or type(air_voltage) != list:
                raise TypeError("Voltages have to be list with multiple sensor_types")
        self.publish_converted_value = publish_converted_value
        self.topic = mqtt_topic or mqtt.getDeviceTopic("soilMoisture")
        interval = interval or config.INTERVAL_SEND_SENSOR
        self._lock = Lock()
        gc.collect()
        asyncio.get_event_loop().create_task(self._loop(self.humidity, interval))

    async def _loop(self, gen, interval):
        while True:
            await gen()
            await asyncio.sleep(interval)

    def _getConverted(self, sensor_type, voltage):
        if voltage is None:
            return None
        air_voltage = self.air_voltage if type(self.air_voltage) != list else self.air_voltage[sensor_type]
        water_voltage = self.water_voltage if type(self.water_voltage) != list else self.water_voltage[sensor_type]
        if sensor_type == 0:  # std sensor
            interval = (water_voltage - air_voltage) / 3
            # TODO: check if calculations make sense
            if voltage > water_voltage - interval:
                return "wet"
            elif voltage > air_voltage + interval:
                return "humid"
            else:
                return "dry"
        elif sensor_type == 1:  # capacitive
            interval = (air_voltage - water_voltage) / 3
            if voltage > air_voltage - interval:
                return "dry"
            elif voltage > water_voltage + interval:
                return "humid"
            else:
                return "wet"
        else:
            raise NotImplementedError("Sensor type {!s} not implemented".format(sensor_type))

    def _getPercentage(self, sensor_type, voltage):
        if voltage is None:
            return None
        air_voltage = self.air_voltage if type(self.air_voltage) != list else self.air_voltage[sensor_type]
        water_voltage = self.water_voltage if type(self.water_voltage) != list else self.water_voltage[sensor_type]
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

    async def _read(self, publish=True):
        res = []
        i = 0
        async with self._lock:
            if type(self.sensor_types) == list:
                sensors = self.sensor_types
            elif type(self.adc) == ADC:
                sensors = [self.sensor_types]
            else:
                sensors = [self.sensor_types] * self.adc.getSize()
            for sensor in sensors:
                if self.power_pin is not None:
                    if type(self.power_pin) == list:
                        self.power_pin[sensor].value(1)
                    else:
                        self.power_pin.value(1)
                    await asyncio.sleep_ms(self.power_warmup)
                voltage = None
                if sensor is None:
                    res.append(None)
                else:
                    voltage = 0
                    for j in range(3):
                        voltage += self._adc_read() if type(self.adc) == ADC else self._adc_read(i)
                    voltage /= 3
                    res.append(self._getPercentage(sensor, voltage))
                if publish:
                    log.debug(self.topic + "/" + str(i) + ": " + str(res[-1]), local_only=True)
                    await mqtt.publish(self.topic + "/" + str(i), res[-1])
                    if self.publish_converted_value:
                        await mqtt.publish(self.topic + "/" + str(i) + "/conv",
                                           self._getConverted(sensor, voltage))
                if self.power_pin is not None:
                    if type(self.power_pin) == list:
                        self.power_pin[sensor].value(0)
                    else:
                        self.power_pin.value(0)
                gc.collect()
                i += 1
        if len(res) == 0:
            return None
        elif len(res) == 1:
            return res[0]
        return res

    async def humidity(self, publish=True):
        return await self._read(publish=publish)
