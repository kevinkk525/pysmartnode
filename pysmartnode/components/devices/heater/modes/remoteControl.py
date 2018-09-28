'''
Created on 2018-08-13

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.heater.modes.remoteControl
    component: remoteControl
    constructor_args: {
        HEATER: heaterObject    # name of heater object registered before this component
        ACTIVE: False           # optional, if mode should be activated immediately (or just be available if needed later)
    }
}
Fully remotely controlled heater mode. Will just set the power received by mqtt.
Be aware that heater will switch to internal mode if temp < FROST or temp >SHUTDOWN_TEMP
"""

__updated__ = "2018-08-13"
__version__ = "0.1"

from ..core import log, _mqtt

__heater = None


async def remoteControl(HEATER, ACTIVE=False):
    global __heater
    __heater = HEATER
    HEATER.addMode("REMOTE", _remoteMode)
    await _mqtt.subscribe(HEATER.getPowerTopic() + "/set", _requestPower, qos=1)
    log.info("Heater mode 'remoteControl' version {!s}".format(__version__))
    if ACTIVE:
        HEATER.setMode("", "REMOTE", False)


async def _requestPower(topic, msg, retain):
    # if heater mode == "INTERNAL" this will have no effect because main loop does not check for it
    heater = __heater
    try:
        power = float(msg)
    except:
        log.error("Error converting requested power to float: {!r}".format(msg))
        return None
    await heater.setTargetPower(power)
    log.debug("requestPower {!s}".format(power), local_only=True)
    if heater.getActiveMode() == "INTERNAL" and retain is False:
        # don't log if it's a retained value because of mc reset
        log.debug("heater in internal mode, requestPower does not work")
    else:
        if heater.hasStarted():
            heater.setEvent()


async def _remoteMode(heater, data):
    # remoteControl only sets the power received by mqtt, which is set by heater.requestPower()
    power = heater.getTargetPower()
    if await heater.setPower(power):
        await _mqtt.publish(heater.getPowerTopic()[:heater.getPowerTopic().find("/set")], power, True, qos=1)
        if power == 0:
            await _mqtt.publish(heater.getStatusTopic(), "OFF", True, qos=1)
        else:
            await _mqtt.publish(heater.getStatusTopic(), "ON", True, qos=1)
        """
        if heater._last_error=="SET_POWER":
            heater._last_error=None
        """
        # Not needed as _watch will reset the last_error if it is the same
    else:
        log.error("Could not set heater power to {!s}%, shutting heater down".format(heater.getStatusTopic()))
        await heater.setHeaterPower(0)
        heater.setLastError("SET_POWER")
        await _mqtt.publish(heater.getPowerTopic()[:heater.getPowerTopic().find("/set")], power, True, qos=1)
        await _mqtt.publish(heater.getStatusTopic(), "ERR: SET_POWER", True, qos=1)
