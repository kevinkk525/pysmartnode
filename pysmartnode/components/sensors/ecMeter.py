# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2019-03-25

"""
example config:
{
    package: .sensors.ecMeter
    component: EC
    constructor_args: {
        r1: 200                # Resistor1, Ohms
        ra: 30                 # Microcontroller Power Pin Resistance
        rg: 30                  # Microcontroller Ground Pin Resistance
        adc: 2                  # ADC pin number, where the EC cable is connected
        power_pin: 4            # Power pin, where the EC cable is connected
        ground_pin: 23          # Ground pin, don't connect EC cable to GND
        ppm_conversion: 0.5     # depends on supplier/country conversion values, see notes
        temp_coef: 0.019        # this changes depending on what chemical are measured, see notes
        k: 2.88                 # Cell Constant, 2.88 for US plug, 1.76 for EU plug, can be calculated/calibrated
        temp_sensor: sens_name  # temperature sensor component, has to provide async temperature()
        # read_timeout: 400     # optional, time (in us) that an ADC read can take before the value will be ignored.
        # iterations: 1         # optional, how often the sensor should be read. average will be used as value
        # precision_ec: 3         # precision of the ec value published
        # friendly_name_ec: null # optional, friendly name shown in homeassistant gui with mqtt discovery
        # friendly_name_ppm: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
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

Readings can be a bit weird. You need to measure your ADC and find calibration values for offset 
and ADC v_max used in .machine.ADC class.
Also the cell constant "k" should be calibrated for the plug you use.
"""

__updated__ = "2021-05-26"
__version__ = "2.0"

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

    def __init__(self, arduino=None, adc=None, power_pin=None, ground_pin=None,
                 r1=300, ra=25, rg=25, ppm_conversion=0.5, temp_coef=0.019, k=2.88,
                 temp_sensor: ComponentSensor = None, read_timeout=400, iterations=1,
                 precision_ec=3, vcc=3.3, friendly_name_ec=None, friendly_name_ppm=None, **kwargs):
        # This makes it possible to use multiple instances of MySensor
        global _unit_index
        _unit_index += 1
        self.checkSensorType(temp_sensor, SENSOR_TEMPERATURE)
        super().__init__(COMPONENT_NAME, __version__, _unit_index, logger=_log, **kwargs)
        self._temp = temp_sensor
        self._addSensorType("ec", precision_ec, 0, VALUE_TEMPLATE_JSON.format("ec|float"), "mS",
                            friendly_name_ec or "EC", self._topic, DISCOVERY_EC)
        self._addSensorType("ppm", 0, 0, VALUE_TEMPLATE_JSON.format("ppm|int"), "ppm",
                            friendly_name_ppm or "PPM", self._topic, DISCOVERY_PPM)
        self._ard=arduino
        if not arduino:
            self._adc = ADC(adc)
            self._ppin = Pin(power_pin, machine.Pin.IN)  # changing to OUTPUT GND when needed
            self._gpin = Pin(ground_pin, machine.Pin.IN)  # changing to OUTPUT GND when needed
        self._r1 = r1
        self._ra = ra
        self._rg = rg
        self._ppm_conversion = ppm_conversion
        self._temp_coef = temp_coef
        self._k = k
        self._to = read_timeout
        self._iters = iterations
        self._vcc = vcc
        gc.collect()

    # @micropython.native
    @staticmethod
    def _read_sync(_gpin_init, _ppin_init, _ppin_value, _adc_read, _in, ticks, ticks_diff):
        a = ticks()
        _ppin_value(1)
        vol = _adc_read()
        b = ticks()
        # vol = _adc_read() # micropython on esp is way too slow to need this, it was for arduino.
        # _ppin_value(0) # if not using ppin as INPUT while not reading
        _gpin_init(_in)
        _ppin_init(_in)
        return vol, ticks_diff(b, a)

    async def _read_arduino(self):
        a = time.ticks_us()
        try:
            adc = await self._ard.read("ec", int, timeout=1000)
        except OSError as e:
            print(e)
            adc=1023 # not connected
        b = time.ticks_us()
        vol = adc/1023*self._ard.getVoltage()
        diff=b-a
        return adc, diff, vol

    async def _read(self):
        temp = await self._temp.getValue(SENSOR_TEMPERATURE)
        if temp is None:
            await asyncio.sleep(30)
            temp = await self._temp.getValue(SENSOR_TEMPERATURE)
            if temp is None:
                _log.warn("Couldn't get temperature, aborting EC measurement")
                return
        vols = []
        diffs = []
        adcs = []
        for _ in range(self._iters):
            if self._ard:
                adc, diff, vol = await self._read_arduino()
            else:
                self._gpin.init(machine.Pin.OUT, value=0)
                self._ppin.init(machine.Pin.OUT, value=0)
                adc, diff = self._read_sync(self._gpin.init, self._ppin.init, self._ppin.value,
                                            self._adc.read, machine.Pin.IN, time.ticks_us,
                                            time.ticks_diff)
                vol = self._adc.convertToVoltage(adc)
            vols.append(vol)
            adcs.append(adc)
            diffs.append(diff)
            if self._iters > 1:
                await asyncio.sleep(20)
        r = []
        for i, diff in enumerate(diffs):
            if diff > self._to:
                r.append(i)
            elif vols[i] >= self._vcc*0.95:
                r.append(i)
        if len(r) == len(diffs):
            vol = vols[0]
            adc = adcs[0]
            diff = diffs[0]
        else:
            for i in range(len(r) - 1, -1, -1):
                diffs.pop(r[i])
                adcs.pop(r[i])
                vols.pop(r[i])
            vol = sum(vols) / len(vols)
            adc = sum(adcs) / len(adcs)
            diff = sum(diffs) / len(diffs)
        if self.DEBUG:
            print("------------")
            print("Time", diff, "us")
            print("Temp", temp)
            print("V", vol, "ADC", adc)
            print("Vols", vols)
            print("adcs", adcs)
            print("diffs", diffs)
        if vol >= self._vcc*0.9:
            await self._setValue("ec", None, log_error=False)
            await self._setValue("ppm", None, log_error=False)
            await _log.asyncLog("warn", "Cable not in fluid")
        else:
            if vol <= 0.5:
                _log.warn("Voltage <=0.5, change resistor")
                await self._setValue("ec", None, log_error=False)
                await self._setValue("ppm", None, log_error=False)
                return
            rc = (vol * (self._r1 + self._ra)) / (self._vcc - vol)
            rc = rc - self._rg
            ec = 1000 / (rc * self._k)
            ec25 = ec / (1 + self._temp_coef * (temp - 25.0))
            ppm = int(ec25 * self._ppm_conversion * 1000)
            if diff > self._to:
                await self._setValue("ec", None, log_error=False)
                await self._setValue("ppm", None, log_error=False)
                _log.warn("Reading timeout, discarding value {!s}V, {!s}ppm".format(vol, ppm))
            else:
                await self._setValue("ec", ec25)
                await self._setValue("ppm", ppm)
                if self.DEBUG:
                    ec25 = round(ec25, 3)
                    print("Rc", rc)
                    print("EC", ec)
                    print("EC25", ec25, "MilliSimens")
                    print("PPM", ppm)
