'''
Created on 2018-08-13

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.heater.modes.remoteControl
    component: RemoteControl
    constructor_args: {
        # HEATER: heaterObject    # optional, name of heater object registered before this component. defaults to the one registered
        # ACTIVE: False           # optional, if mode should be activated immediately (or just be available if needed later)
    }
}
Fully remotely controlled heater mode. Will just set the power received by mqtt.
Be aware that heater will switch to internal mode if temp < FROST or temp >SHUTDOWN_TEMP

Does not support homeassistant discovery as homeassistant doesn't have a component for sending float values.
"""

__updated__ = "2019-06-04"
__version__ = "0.4"

from ..core import log, _mqtt, _heater, Heater
from pysmartnode.utils.component import Component


class RemoteControl(Component):
    def __init__(self, HEATER: Heater = None, ACTIVE=False):
        super().__init__()
        if _heater is None and HEATER is None:
            raise TypeError("No heater unit registered yet")
        self._heater = HEATER or _heater
        self._heater.addMode("REMOTE", self._remoteMode)
        self._subscribe(self._heater.getPowerTopic() + "/set", self._requestPower)
        if ACTIVE is True:
            self._heater.setMode("", "REMOTE", False)

    async def _init_network(self):
        await super()._init_network()
        await log.asyncLog("info", "Heater mode 'remoteControl' version {!s}".format(__version__))

    async def _requestPower(self, topic, msg, retain):
        # if heater mode == "INTERNAL" this will have no effect because main loop does not check for it
        try:
            power = float(msg)
        except ValueError:
            log.error("Error converting requested power to float: {!r}".format(msg))
            return None
        await self._heater.setTargetPower(power)
        log.debug("requestPower {!s}".format(power), local_only=True)
        if self._heater.getActiveMode() == "INTERNAL" and retain is False:
            # don't log if it's a retained value because of mc reset
            await log.asyncLog("debug", "heater in internal mode, requestPower does not work")
        else:
            if self._heater.hasStarted():
                self._heater.setEvent()

    @staticmethod
    async def _remoteMode(heater: Heater, data):
        # remoteControl only sets the power received by mqtt, which is set by heater.requestPower()
        power = heater.getTargetPower()
        if await heater.setHeaterPower(power):
            await _mqtt.publish(heater.getPowerTopic()[:heater.getPowerTopic().find("/set")], power, qos=1, retain=True)
            if power == 0:
                await _mqtt.publish(heater.getStatusTopic(), "OFF", qos=1, retain=True)
            else:
                await _mqtt.publish(heater.getStatusTopic(), "ON", qos=1, retain=True)
            """
            if heater._last_error=="SET_POWER":
                heater._last_error=None
            """
            # Not needed as _watch will reset the last_error if it is the same
        else:
            log.error("Could not set heater power to {!s}%, shutting heater down".format(heater.getStatusTopic()))
            await heater.setHeaterPower(0)
            heater.setLastError("SET_POWER")
            await _mqtt.publish(heater.getPowerTopic()[:heater.getPowerTopic().find("/set")], power, qos=1, retain=True)
            await _mqtt.publish(heater.getStatusTopic(), "ERR: SET_POWER", qos=1, retain=True)
