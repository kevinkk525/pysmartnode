# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-03-25

"""
example config:
{
    package: .sensors.ecMeter
    component: EC
    constructor_args: {
        r1: 200                # Resistor1, Ohms
        ra: 30                 # Microcontroller Pin Resistance
        adc: 2                  # ADC pin number, where the EC cable is connected
        power_pin: 4            # Power pin, where the EC cable is connected
        ground_pin: 23          # Ground pin, don't connect EC cable to GND
        ppm_conversion: 0.64    # depends on supplier/country conversion values, see notes
        temp_coef: 0.019        # this changes depending on what chemical are measured, see notes
        k: 2.88                 # Cell Constant, 2.88 for US plug, 1.76 for EU plug, can be calculated/calibrated
        temp_sensor: sens_name  # temperature sensor component, has to provide async temperature()
        # precision_ec: 3         # precision of the ec value published
        # interval_reading: 600         # optional, defaults to 600
        # interval_public: 600         # optional, defaults to 600
        # mqtt_topic: sometopic   # optional, defaults to home/<controller-id>/ecmeter
        # friendly_name_ec: null # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_ppm: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
"""

"""
Notes:
** Conversion to PPM:
Hana      [USA]        PPMconverion:  0.5
Eutech    [EU]         PPMconversion:  0.64
Tranchen  [Australia]  PPMconversion:  0.7

** Temperature Compensation:
The value temp_coef depends on the chemical solution.
0.019 is generaly considered the standard for plant nutrients [google "Temperature compensation EC" for more info]

** How to connect:
Put R1 between the power pin and the adc pin.
Connect the ec cable to the adc pin and ground pin.

** Inspiration from:
https://hackaday.io/project/7008-fly-wars-a-hackers-solution-to-world-hunger/log/24646-three-dollar-ec-ppm-meter-arduino
https://www.hackster.io/mircemk/arduino-electrical-conductivity-ec-ppm-tds-meter-c48201
After many hours of testing and trying optimize reading speeds, it turned out that the readins
were actually as "accurate" as the original sketch on the Arduino Uno.
Results were: Accurate around 300ppm, at 700ppm only 550ppm were read..
However, the bigger the used resistor, the worse the readings got. 100-200R was actually best.
"""

__updated__ = "2020-03-19"
__version__ = "1.4"

from pysmartnode import config
from pysmartnode import logging
from pysmartnode.components.machine.adc import ADC
from pysmartnode.components.machine.pin import Pin
import uasyncio as asyncio
import gc
import machine
from pysmartnode.utils.component.sensor import ComponentSensor, SENSOR_TEMPERATURE
from pysmartnode.utils.component.definitions import VALUE_TEMPLATE_JSON
import micropython
import time

COMPONENT_NAME = "ECmeter"
_COMPONENT_TYPE = "sensor"

DISCOVERY_EC = '"unit_of_meas":"mS",' \
               '"val_tpl":"{{ value_json.ec|float }}",' \
               '"ic":"mdi:alpha-e-circle-outline",'

DISCOVERY_PPM = '"unit_of_meas":"ppm",' \
                '"val_tpl":"{{ value_json.ppm|int }}",' \
                '"ic":"mdi:alpha-p-circle-outline",'

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()

_unit_index = -1


class EC(ComponentSensor):
    DEBUG = True

    def __init__(self, r1, ra, adc, power_pin, ground_pin, ppm_conversion, temp_coef, k,
                 temp_sensor: ComponentSensor, precision_ec=3, interval_publish=None,
                 interval_reading=None,
                 mqtt_topic=None, friendly_name_ec=None, friendly_name_ppm=None,
                 discover=True, expose_intervals=False, intervals_topic=None):
        # This makes it possible to use multiple instances of MySensor
        global _unit_index
        _unit_index += 1
        self.checkSensorType(temp_sensor, SENSOR_TEMPERATURE)
        super().__init__(COMPONENT_NAME, __version__, _unit_index, discover, interval_publish,
                         interval_reading, mqtt_topic, _log, expose_intervals, intervals_topic)
        self._temp = temp_sensor
        self._addSensorType("ec", precision_ec, 0, VALUE_TEMPLATE_JSON.format("ec|float"), "mS",
                            friendly_name_ec or "EC", mqtt_topic, DISCOVERY_EC)
        self._addSensorType("ppm", 0, 0, VALUE_TEMPLATE_JSON.format("ppm|int"), "ppm",
                            friendly_name_ppm or "PPM", mqtt_topic, DISCOVERY_PPM)

        self._adc = ADC(adc)
        self._ppin = Pin(power_pin, machine.Pin.IN)  # changing to OUTPUT GND when needed
        self._gpin = Pin(ground_pin, machine.Pin.IN)  # changing to OUTPUT GND when needed
        self._r1 = r1
        self._ra = ra
        self._ppm_conversion = ppm_conversion
        self._temp_coef = temp_coef
        self._k = k
        gc.collect()

    @micropython.native
    @staticmethod
    def _read_sync(_gpin_init, _ppin_init, _ppin_value, _adc_read, _in, ticks, ticks_diff):
        a = ticks()
        _ppin_value(1)
        vol = _adc_read()
        b = ticks()
        # vol = _adc_read() # micropython on esp is way too slow to need this, it was for arduino.
        _gpin_init(_in)
        _ppin_init(_in)
        return vol, ticks_diff(b, a)

    async def _read(self):
        temp = await self._temp.getValue(SENSOR_TEMPERATURE)
        if temp is None:
            await asyncio.sleep(3)
            temp = await self._temp.getValue(SENSOR_TEMPERATURE)
            if temp is None:
                _log.warn("Couldn't get temperature, aborting EC measurement")
                return
        vols = []
        diffs = []
        for i in range(5):
            self._gpin.init(machine.Pin.OUT, value=0)
            self._ppin.init(machine.Pin.OUT, value=0)
            await asyncio.sleep_ms(20)
            vol, diff = self._read_sync(self._gpin.init, self._ppin.init, self._ppin.value,
                                        self._adc.read, machine.Pin.IN, time.ticks_us,
                                        time.ticks_diff)
            vol = self._adc.convertToVoltage(vol)
            vols.append(vol)
            diffs.append(diff)
            await asyncio.sleep(1)
        vol = min(vols)
        diff = min(diffs)
        if self.DEBUG:
            print("------------")
            print("Time", diff, "us")
            print("Temp", temp)
            print("V", vol)
            print("Vols", vols)
            print("Diff", diffs)
        if vol >= self._adc.maxVoltage():
            await self._setValue("ec", None, log_error=False)
            await self._setValue("ppm", None, log_error=False)
            await _log.asyncLog("warn", "Cable not in fluid")
        else:
            if vol <= 0.5:
                _log.warn("Voltage <=0.5, change resistor")
            rc = (vol * (self._r1 + self._ra)) / (self._adc.maxVoltage() - vol)
            rc = rc - self._ra
            ec = 1000 / (rc * self._k)
            ec25 = ec / (1 + self._temp_coef * (temp - 25.0))
            ppm = int(ec25 * self._ppm_conversion * 1000)
            await self._setValue("ec", ec25)
            await self._setValue("ppm", ppm)
            if self.DEBUG:
                ec25 = round(ec25, 3)
                print("Rc", rc)
                print("EC", ec)
                print("EC25", ec25, "MilliSimens")
                print("PPM", ppm)
