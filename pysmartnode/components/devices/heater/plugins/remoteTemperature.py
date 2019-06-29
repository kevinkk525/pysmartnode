'''
Created on 2018-09-25

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.heater.plugins.remoteTemperature
    component: RemoteTemperature
    constructor_args: {
        # HEATER: heaterObject  # optional, name of heater object registered before this component
        TOPIC: sometopic        # topic of the remote temperature, supports float or dict with "temperature":float
    }
}
Adds support for receiving temperature over mqtt and use it to control the heater power.
This plugin works completely independent of other modules and modes and will overwrite the "current_temp" attribute

Does not support homeassistant discovery as homeassistant doesn't have a component for sending a string.
"""

__updated__ = "2019-06-04"
__version__ = "0.8"

from ..core import log, _heater, Heater
import time
from pysmartnode.utils.component import Component


class RemoteTemperature(Component):
    def __init__(self, TOPIC, HEATER: Heater = None):
        super().__init__()
        if HEATER is None and _heater is None:
            raise TypeError("No heater unit registered yet")
        self._heater = HEATER or _heater
        self._heater.registerPlugin(self._remoteTempControl, "remoteTemperature")
        self._subscribe(TOPIC, self._remoteTemp)
        log.info("Heater plugin 'remoteTemperature' version {!s}".format(__version__))
        self.__time = None
        self.__temp = None

    async def _remoteTemp(self, topic, msg, retain):
        if retain:
            # a retained temperature value is of no use
            return
        if type(msg) == dict:
            if "temperature" in msg:
                msg = msg["temperature"]
            else:
                log.error("Dictionary has unsupported values")
                return
        try:
            msg = float(msg)
        except Exception as e:
            log.error("Can't convert remote temperature to float: {!s}".format(e))
            return
        self.__time = time.ticks_ms()
        self.__temp = msg
        log.debug("Got remote temp {!s}°C".format(msg), local_only=True)

    async def _remoteTempControl(self, heater, data):
        if self.__temp is not None:
            if time.ticks_ms() - self.__time < heater.getInterval() * 1000:
                data["current_temp"] = self.__temp
                # overwriting current_temp, if no remote temp received, internal temp is used
                log.debug("Using remote temperature {!s}°C".format(self.__temp), local_only=True)
        data["remote_temp"] = self.__temp
        data["remote_temp_time"] = self.__time
        # just in case a future plugin would like to use this
