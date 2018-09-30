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
        #interval: 600            #optional, defaults to 600, 0 means publish every value received
        #mqtt_topic: sometopic  #optional, defaults to home/<controller-id>/PMS5003
    }
}
Sensor can only be used with esp32 as esp8266 has only 1 uart at 115200 (9600 needed) 
"""

__updated__ = "2018-08-31"
__version__ = "1.2"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
import gc
import machine

####################
# import your library here
from pysmartnode.libraries.pms5003 import pms5003 as sensorModule

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
_component_name = "PMS5003"
####################

_log = logging.getLogger(_component_name)
_mqtt = config.getMQTT()
gc.collect()


class PMS5003(sensorModule.PMS5003):
    def __init__(self, uart_number, uart_tx, uart_rx, set_pin=None, reset_pin=None,
                 interval_passive_mode=None, active_mode=True, eco_mode=True,
                 interval=None, mqtt_topic=None):
        interval = interval or config.INTERVAL_SEND_SENSOR
        interval_passive_mode = interval_passive_mode or interval
        self.topic = mqtt_topic or _mqtt.getDeviceTopic(_component_name)
        uart = machine.UART(uart_number, tx=uart_tx, rx=uart_rx, baudrate=9600)

        ##############################
        # create sensor object
        super().__init__(uart, config.Lock(), set_pin, reset_pin, interval_passive_mode,
                         active_mode=active_mode, eco_mode=eco_mode)
        gc.collect()
        if (interval == interval_passive_mode and active_mode is False) or interval == 0:
            self.registerCallback(self.airQuality)
        else:
            # possible to have different timings in passive_read and publish interval
            # useful if other components use readings of sensor too
            asyncio.get_event_loop().create_task(self._loop(self.airQuality(), interval))

    async def _loop(self, gen, interval):
        while True:
            await gen()
            await asyncio.sleep(interval)

    ##############################
    # remove or add functions below depending on the values of your sensor

    async def airQuality(self, publish=True):
        if self._active and self._timestamp is not None:  # timestamp is None if no value received yet
            values = {
                "pm10_standard": self._pm10_standard,
                "pm25_standard": self._pm25_standard,
                "pm100_standard": self._pm100_standard,
                "pm10_env": self._pm10_env,
                "pm25_env": self._pm25_env,
                "pm100_env": self._pm100_env,
                "particles_03um": self._particles_03um,
                "particles_05um": self._particles_05um,
                "particles_10um": self._particles_10um,
                "particles_25um": self._particles_25um,
                "particles_50um": self._particles_50um,
                "particles_100um": self._particles_100um
            }
            if publish:
                await _mqtt.publish(self.topic, values)
            return values
        else:
            return None

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
