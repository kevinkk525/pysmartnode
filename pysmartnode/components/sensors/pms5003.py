'''
Created on 16.06.2018

@author: Kevin Köck
'''

"""
example config:
{
    package: .sensors.pms5003
    component: PMS5003
    constructor_args: {
        uart_number: 1     # uart number (esp32 has 3 uarts)
        uart_tx: 25        # uart tx pin
        uart_rx: 26        # uart rx pin
        # set_pin: null    # optional, sets device to sleep/wakes it up, can be done with uart
        # reset_pin: null   # optional, without this pin the device can not be reset
        # interval_passive_mode: null   # optional, only used in passive mode, defaults to interval
        # active_mode: true     # optional, defaults to true, in passive mode device is in sleep between measurements
        # eco_mode: true        # optional, defaults to true, puts device to sleep between passive reads
        # interval: 600            #optional, defaults to 600, 0 means publish every value received
        # mqtt_topic: sometopic  #optional, defaults to home/<controller-id>/PMS5003
        # friendly_name: [...]   # optional, list of friendly names for each published category
    }
}
Sensor can only be used with esp32 as esp8266 has only 1 uart at 115200 (9600 needed) 
"""

__updated__ = "2019-10-21"
__version__ = "1.7"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import gc
import machine
from pysmartnode.utils.component import Component

DISCOVERY_PM = '"unit_of_meas":"{!s}",' \
               '"val_tpl":"{!s}",'

####################
# import your library here
from pysmartnode.libraries.pms5003 import pms5003 as sensorModule

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "PMS5003"
_COMPONENT_TYPE = "sensor"
####################

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()


class PMS5003(sensorModule.PMS5003, Component):
    def __init__(self, uart_number, uart_tx, uart_rx, set_pin=None, reset_pin=None,
                 interval_passive_mode=None, active_mode=True, eco_mode=True,
                 interval=None, mqtt_topic=None, friendly_name: list = None):
        Component.__init__(self, COMPONENT_NAME, __version__)
        self._interval = interval or config.INTERVAL_SEND_SENSOR
        self._int_pm = interval_passive_mode or self._interval
        self._topic = mqtt_topic
        if type(friendly_name) is not None:
            if type(friendly_name) == list:
                if len(friendly_name) != 12:
                    _log.warn("Length of friendly name is wrong, expected 12 got {!s}".format(
                        len(friendly_name)))
                    self._frn = None
                else:
                    self._frn = friendly_name
            else:
                _log.warn("Friendly name got unsupported type {!s}, expect list".format(
                    type(friendly_name)))
                self._frn = None
        else:
            self._frn = None
        uart = machine.UART(uart_number, tx=uart_tx, rx=uart_rx, baudrate=9600)

        ##############################
        # create sensor object
        sensorModule.PMS5003.__init__(self, uart, config.Lock(), set_pin, reset_pin,
                                      interval_passive_mode,
                                      active_mode=active_mode, eco_mode=eco_mode)
        gc.collect()
        if (self._interval == self._int_pm and self._active_mode is False) or self._interval == 0:
            self.registerCallback(self.airQuality)
        else:
            asyncio.get_event_loop().create_task(self._loop())

    async def _loop(self):
        while True:
            await self.airQuality()
            await asyncio.sleep(self._interval)

    async def _discovery(self):
        values = ["pm10_standard", "pm25_standard", "pm100_standard", "pm10_env", "pm25_env",
                  "pm100_env", "particles_03um", "particles_05um", "particles_10um",
                  "particles_25um", "particles_50um", "particles_100um"]
        meas = ["µg/m3", "µg/m3", "µg/m3", "µg/m3", "µg/m3",
                "µg/m3", "1/0.1L", "1/0.1L", "1/0.1L",
                "1/0.1L", "1/0.1L", "1/0.1L", ]
        for i in range(len(values)):
            value = values[i]
            name = "{!s}/{!s}".format(COMPONENT_NAME, value)
            sens = DISCOVERY_PM.format(meas[i],  # unit_of_measurement
                                       "{{ value_json.{!s} }}".format(value))  # value_template
            await self._publishDiscovery(_COMPONENT_TYPE, self.airQualityTopic(), name, sens,
                                         self._frn[i] or value)
            del name, sens
            gc.collect()

    ##############################
    # remove or add functions below depending on the values of your sensor

    async def airQuality(self, publish=True, timeout=5, no_stale=False) -> dict:
        """Method for publishing values.
        There is a method for each value in the base class.
        no_stale: PMS sensor doesn't support getting live values,
        use active mode with Event or callback"""
        if self._active and self._timestamp is not None:
            # timestamp is None if no value received yet
            values = {
                "pm10_standard":   self._pm10_standard,
                "pm25_standard":   self._pm25_standard,
                "pm100_standard":  self._pm100_standard,
                "pm10_env":        self._pm10_env,
                "pm25_env":        self._pm25_env,
                "pm100_env":       self._pm100_env,
                "particles_03um":  self._particles_03um,
                "particles_05um":  self._particles_05um,
                "particles_10um":  self._particles_10um,
                "particles_25um":  self._particles_25um,
                "particles_50um":  self._particles_50um,
                "particles_100um": self._particles_100um
            }
            if publish:
                await _mqtt.publish(self.airQualityTopic(), values, timeout=timeout,
                                    await_connection=False)
            return values
        else:
            return None

    @staticmethod
    def airQualityTemplate():
        raise TypeError("Multiple value templates")

    def airQualityTopic(self):
        return self._topic or _mqtt.getDeviceTopic(COMPONENT_NAME)

    ##############################

    @staticmethod
    def _error(message):
        _log.error(message)

    @staticmethod
    def _warn(message):
        _log.warn(message)

    @staticmethod
    def _debug(message):
        if sensorModule.DEBUG:
            _log.debug(message, local_only=True)

    @staticmethod
    def set_debug(value):
        sensorModule.set_debug(value)
