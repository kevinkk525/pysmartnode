# Author: Kevin Köck
# Copyright Kevin Köck 2018-2019 Released under the MIT license
# Created on 2018-06-16

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
        # interval_reading: 0.1   # optional, In passive mode controls the reading interval, defaults to 0.1 in active_mode.
        # interval_publish: 600   # publish interval, independent of interval_reading and active_mode, defaults to 600s
        # active_mode: true     # optional, defaults to true, in passive mode device is in sleep between measurements
        # eco_mode: true        # optional, defaults to true, puts device to sleep between passive reads
        # interval: 600            #optional, defaults to 600, 0 means publish every value received
        # mqtt_topic: sometopic  #optional, defaults to home/<controller-id>/PMS5003
        # friendly_name: [...]   # optional, list of friendly names for each published category
        # discover: true            # optional, if false no discovery message for homeassistant will be sent.
        # expose_intervals: Expose intervals to mqtt so they can be changed remotely
        # intervals_topic: if expose_intervals then use this topic to change intervals. Defaults to <home>/<device-id>/<COMPONENT_NAME><_count>/interval/set. Send a dictionary with keys "reading" and/or "publish" to change either/both intervals.
    }
}
Sensor can only be used with esp32 as esp8266 has only 1 uart at 115200 (9600 needed) 
"""

__updated__ = "2019-10-29"
__version__ = "1.8"

from pysmartnode import config
from pysmartnode import logging
import gc
import machine
from pysmartnode.utils.component.sensor import ComponentSensor, VALUE_TEMPLATE_JSON

DISCOVERY_PM = '"unit_of_meas":"{!s}",' \
               '"val_tpl":"{{{{ value_json.{!s} }}}}",'

TYPES = ["pm10_standard", "pm25_standard", "pm100_standard", "pm10_env", "pm25_env",
         "pm100_env", "particles_03um", "particles_05um", "particles_10um",
         "particles_25um", "particles_50um", "particles_100um"]

UNITS = ["µg/m3", "µg/m3", "µg/m3", "µg/m3", "µg/m3",
         "µg/m3", "1/0.1L", "1/0.1L", "1/0.1L",
         "1/0.1L", "1/0.1L", "1/0.1L"]

####################
# import your library here
from pysmartnode.libraries.pms5003 import pms5003 as sensorModule

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
COMPONENT_NAME = "PMS5003"
####################

_log = logging.getLogger(COMPONENT_NAME)
_mqtt = config.getMQTT()
gc.collect()


class PMS5003(ComponentSensor):
    def __init__(self, uart_number, uart_tx, uart_rx, set_pin=None, reset_pin=None,
                 interval_reading=0.1, active_mode=True, eco_mode=True,
                 interval_publish=None, mqtt_topic=None, friendly_name: list = None,
                 discover=True, expose_intervals=False, intervals_topic=None):
        """
        :param uart_number: esp32 has multiple uarts
        :param uart_tx: tx pin number
        :param uart_rx: rx pin number
        :param set_pin: optional pin number for set pin
        :param reset_pin: optional pin number for reset pin
        :param interval_reading: In passive mode controls the reading interval, defaults to 0.1 in active_mode.
        :param active_mode:
        :param eco_mode:
        :param interval_publish: publish interval, independent of interval_reading and active_mode
        :param mqtt_topic:
        :param friendly_name: optional, list of friendly_names for all types. Has to provide a name for every type.
        :param discover:
        :param expose_intervals: intervals can be changed through mqtt
        :param intervals_topic:
        """
        super().__init__(COMPONENT_NAME, __version__, discover, interval_publish, interval_reading,
                         mqtt_topic, _log, expose_intervals, intervals_topic)
        if type(friendly_name) is not None:
            if type(friendly_name) == list:
                if len(friendly_name) != 12:
                    _log.warn("Length of friendly name is wrong, expected 12 got {!s}".format(
                        len(friendly_name)))
                    friendly_name = None
            else:
                _log.warn("Friendly name got unsupported type {!s}, expect list".format(
                    type(friendly_name)))
                friendly_name = None
        for tp in TYPES:
            ind = TYPES.index(tp)
            self._addSensorType(tp, 0, 0, VALUE_TEMPLATE_JSON.format(tp), UNITS[ind],
                                friendly_name[ind] if friendly_name is not None else tp,
                                None, DISCOVERY_PM.format(UNITS[ind], tp))
        uart = machine.UART(uart_number, tx=uart_tx, rx=uart_rx, baudrate=9600)
        self._count = 0

        ##############################
        # create sensor object
        self.pms = sensorModule.PMS5003(self, uart, config.Lock(), set_pin, reset_pin,
                                        interval_reading, active_mode=active_mode,
                                        eco_mode=eco_mode)
        self._active_mode = active_mode
        gc.collect()
        if self._active_mode is False:
            # in passive mode using callback because reading intervals could drift apart
            # between sensor and ComponentSensor
            self.pms.registerCallback(self._saveVals)

    async def _read(self):
        if self._active_mode:
            await self._saveVals(is_callback=False)
        # in passive mode callback will set values

    async def _saveVals(self, is_callback=True):
        for tp in TYPES:
            await self._setValue(tp, getattr(self.pms, tp), timeout=0 if is_callback else 10)

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
