# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-03-25 

__updated__ = "2019-03-26"
__version__ = "0.1"

"""
example config:
{
    package: .sensors.ecMeter
    component: EC
    constructor_args: {
        r1: 1000                # Resistor1, Ohms
        ra: 200                 # Microcontroller Pin Resistance
        adc: 2                  # ADC pin number, where the EC cable is connected 
        power_pin: 4            # Power pin, where the EC cable is connected
        ppm_conversion: 0.64    # depends on cable used, see notes
        temp_coef: 0.019        # this changes depending on what chemical are measured, see notes
        k: 2.88                 # Cell Constant, 2.88 for US plug, 1.76 for EU plug, can be calculated/calibrated
        temp_sensor: sens_name  # temperature sensor component, has to provide async temperature()
        precision_ec: 3         # precision of the ec value published             
        # interval: 600         # optional, defaults to 600
        # topic_ec: sometopic   # optional, defaults to home/<controller-id>/EC
        # topic_ppm: sometopic  # optional, defaults to home/<controller-id>/PPM
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
Connect the ec cable to the adc pin and gnd.

** Inspiration from:
https://hackaday.io/project/7008-fly-wars-a-hackers-solution-to-world-hunger/log/24646-three-dollar-ec-ppm-meter-arduino
https://www.hackster.io/mircemk/arduino-electrical-conductivity-ec-ppm-tds-meter-c48201
"""

from pysmartnode import config
from pysmartnode import logging
from pysmartnode.components.machine.adc import ADC
from pysmartnode.components.machine.pin import Pin
import uasyncio as asyncio
import gc
import machine
import time

_component_name = "ECmeter"

_log = logging.getLogger(_component_name)
_mqtt = config.getMQTT()
gc.collect()


# TODO: add some connectivity checks of the "sensor"

class EC:
    def __init__(self, r1, ra, adc, power_pin, ppm_conversion, temp_coef, k, temp_sensor,
                 precision_ec=3, interval=None, topic_ec=None, topic_ppm=None):
        interval = interval or config.INTERVAL_SEND_SENSOR
        self._topic_ec = topic_ec or _mqtt.getDeviceTopic("EC")
        self._topic_ppm = topic_ppm or _mqtt.getDeviceTopic("PPM")
        self._prec_ec = int(precision_ec)
        self._adc = ADC(adc)
        self._ppin = Pin(power_pin, machine.Pin.OUT)
        self._r1 = r1
        self._ra = ra
        self._ppm_conversion = ppm_conversion
        self._temp_coef = temp_coef
        self._k = k
        self._temp = temp_sensor
        if hasattr(temp_sensor, "temperature") is False:
            raise AttributeError(
                "Temperature sensor {!s}, type {!s} has no async method temperature()".format(temp_sensor,
                                                                                              type(temp_sensor)))
        gc.collect()
        self._ec25 = None
        self._ppm = None
        self._time = 0
        asyncio.get_event_loop().create_task(self._loop(self._read, interval))

    @staticmethod
    async def _loop(gen, interval):
        while True:
            await gen()
            await asyncio.sleep(interval)

    async def _read(self, publish=True):
        if time.ticks_ms() - self._time < 5000:
            self._time = time.ticks_ms()
            await asyncio.sleep(5)
        temp = await self._temp.temperature(publish=False)
        if temp is None:
            await asyncio.sleep(3)
            temp = await self._temp.temperature(publish=False)
            if temp is None:
                _log.warn("Couldn't get temperature, aborting EC measurement")
                self._ec25 = None
                self._ppm = None
                return None, None
        print("Temp", temp)
        self._ppin.value(1)
        vol = self._adc.readVoltage()
        print("V", vol)
        # vol = self._adc.readVoltage()
        # print("V", vol)
        # micropython on esp is probably too slow to need this. It was intended for arduino
        self._ppin.value(0)
        if vol >= self._adc.maxVoltage():
            ec25 = 0
            ppm = 0
            _log.warn("Cable not in fluid")
        else:
            if vol <= 0.5:
                _log.warn("Voltage <=0.5, change resistor")
            rc = (vol * (self._r1 + self._ra)) / (self._adc.maxVoltage() - vol)
            # rc = rc - self._ra # sensor connected to ground, not a pin, therefore no Ra
            print("Rc", rc)
            ec = 1000 / (rc * self._k)
            print("EC", ec)
            ec25 = ec / (1 + self._temp_coef * (temp - 25.0))
            print("EC25", ec25, "MilliSimens")
            ppm = int(ec25 * self._ppm_conversion * 1000)
            print("PPM", ppm)
            ec25 = round(ec25, self._prec_ec)
        self._ec25 = ec25
        self._ppm = ppm
        self._time = time.ticks_ms()

        if publish:
            await _mqtt.publish(self._topic_ec, ("{0:." + str(self._prec_ec) + "f}").format(ec25))
            await _mqtt.publish(self._topic_ppm, ppm)
        return ec25, ppm

    async def ec(self, publish=True):
        if time.ticks_ms() - self._time > 5000:
            await self._read(publish)
        return self._ec25

    async def ppm(self, publish=True):
        if time.ticks_ms() - self._time > 5000:
            await self._read(publish)
        return self._ppm
