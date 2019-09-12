# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-07-03

"""
example config:
{
    package: .unix.rf433switch
    component: RF433
    constructor_args: {
        unit_code: "10001"
        unit: "1"
        # expected_execution_time_on: 500  # optional, estimated execution time; allows other coroutines to run during that time
        # expected_execution_time_off: 500 # optional, estimated execution time; allows other coroutines to run during that time
        # iterations: 1                   # optional, number of times the command will be executed
        # iter_delay: 20                  # optional, delay in ms between iterations
        # mqtt_topic: null     #optional, defaults to <mqtt_home>/<device_id>/RF433<count>/set
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
"""

__updated__ = "2019-09-08"
__version__ = "0.3"

import gc
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.component import Switch, DISCOVERY_SWITCH
from .popen_base import Popen

####################
COMPONENT_NAME = "RF433Switch"
# define the type of the component according to the homeassistant specifications
_COMPONENT_TYPE = "switch"
####################

_mqtt = config.getMQTT()
_log = logging.getLogger(COMPONENT_NAME)

gc.collect()

_count = 0

COMMAND_ON = "~/raspberry-remote/send {!s} {!s} 1"
COMMAND_OFF = "~/raspberry-remote/send {!s} {!s} 0"
EXPECTED_RETURN_ON = 'using pin 0\nsending systemCode[{!s}] unitCode[{!s}] command[1]\n'
EXPECTED_RETURN_OFF = 'using pin 0\nsending systemCode[{!s}] unitCode[{!s}] command[0]\n'


class RF433(Switch):
    lock = config.Lock()  # only one method can have control over the RF433 device

    def __init__(self, unit_code, unit, expected_execution_time_on=500, expected_execution_time_off=500,
                 iterations=1, iter_delay=10, mqtt_topic=None, friendly_name=None):
        super().__init__()
        self._log = _log

        # This makes it possible to use multiple instances of Switch
        global _count
        self._count = _count
        _count += 1
        self._topic = mqtt_topic or _mqtt.getDeviceTopic("{!s}{!s}".format(COMPONENT_NAME, self._count),
                                                         is_request=True)
        self._subscribe(self._topic, self.on_message)
        self._frn = friendly_name
        gc.collect()
        self.unit_lock = config.Lock()
        self._c_on = Popen(COMMAND_ON.format(unit_code, unit), EXPECTED_RETURN_ON.format(unit_code, unit),
                           expected_execution_time_on, iterations, iter_delay)
        self._c_off = Popen(COMMAND_OFF.format(unit_code, unit), EXPECTED_RETURN_OFF.format(unit_code, unit),
                            expected_execution_time_off, iterations, iter_delay)

    async def on_message(self, topic, msg, retain):
        if self.unit_lock.locked():
            return False
        async with self.lock:
            async with self.unit_lock:
                if msg in _mqtt.payload_on:
                    r = await self._c_on.execute()
                    if r is True:
                        await _mqtt.publish(self._topic[:-4], "ON", qos=1, retain=True)  # makes it easier to subclass
                        return True
                    else:
                        await self._log.asyncLog("warn", "Got unexpected return: {!s}".format(r))
                        return False
                elif msg in _mqtt.payload_off:
                    r = await self._c_off.execute()
                    if r is True:
                        await _mqtt.publish(self._topic[:-4], "OFF", qos=1, retain=True)
                        return True
                    else:
                        await self._log.asyncLog("warn", "Got unexpected return: {!s}".format(r))
                        return False

    async def _discovery(self):
        name = "{!s}{!s}".format(COMPONENT_NAME, self._count)
        await self._publishDiscovery(_COMPONENT_TYPE, self._topic[:-4], name, DISCOVERY_SWITCH, self._frn)
        # note that _publishDiscovery does expect the state topic but we have the command topic stored.
