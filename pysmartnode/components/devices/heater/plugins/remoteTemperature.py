'''
Created on 2018-09-25

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.heater.plugins.remoteTemperature
    component: remoteTemperature
    constructor_args: {
        HEATER: heaterObject    # name of heater object registered before this component
        TOPIC: sometopic        # topic of the remote temperature, supports float or dict with "temperature":float
    }
}
Adds support for receiving temperature over mqtt and use it to control the heater power.
This plugin works completely independent of other modules and modes and will overwrite the "current_temp" attribute
"""

__updated__ = "2018-09-29"
__version__ = "0.3"

from ..core import log, _mqtt
import time


async def remoteTemperature(HEATER, TOPIC):
    HEATER.registerPlugin(_remoteTempControl, "remoteTemperature")
    await _mqtt.subscribe(TOPIC, _remoteTemp, qos=0)
    await log.asyncLog("info", "Heater plugin 'remoteTemperature' version {!s}".format(__version__))


__time = None
__temp = None


async def _remoteTemp(topic, msg, retain):
    global __time
    global __temp
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
    __time = time.ticks_ms()
    __temp = msg
    log.debug("Got remote temp {!s}°C".format(msg), local_only=True)


async def _remoteTempControl(heater, data):
    if __temp is not None:
        if time.ticks_ms() - __time < heater.getInterval() * 1000:
            data["current_temp"] = __temp  # overwriting current_temp, if no remote temp received, internal temp is used
            log.debug("Using remote temperature {!s}°C".format(__temp), local_only=True)
    data["remote_temp"] = __temp
    data["remote_temp_time"] = __time
    # just in case a future plugin would like to use this
