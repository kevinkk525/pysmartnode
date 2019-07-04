# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-07-02

"""
example config:
{
    package: .unix.switch
    component: Switch
    constructor_args: {
        command_on: "something"         # command to execute when switch gets switched off
        expected_return_on: "True"      # optional, expected output of command_on. If not provided, output is being published
        expected_execution_time_on: 50  # optional, estimated execution time; allows other coroutines to run during that time
        command_off: "something"        # command to execute when switch gets switched off
        expected_return_off: "True"     # optional, expected output of command_on. If not provided, output is being published
        expected_execution_time_off: 50 # optional, estimated execution time; allows other coroutines to run during that time
        iterations: 1                   # optional, number of times the command will be executed
        iter_delay: 20                  # optional, delay in ms between iterations
        # mqtt_topic: null     #optional, defaults to <mqtt_home>/<device_id>/UnixSwitch<count>/set
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
"""

__updated__ = "2019-07-03"
__version__ = "0.3"

import gc
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.component import Component, DISCOVERY_SWITCH
from .popen_base import Popen

####################
_component_name = "UnixSwitch"
# define the type of the component according to the homeassistant specifications
_component_type = "switch"
####################

_mqtt = config.getMQTT()
_log = logging.getLogger(_component_name)

gc.collect()

_count = 0


class Switch(Component):
    def __init__(self, command_on, command_off, expected_return_on=None, expected_execution_time_on=0,
                 expected_return_off=None, expected_execution_time_off=0,
                 iterations=1, iter_delay=10, mqtt_topic=None, friendly_name=None):
        super().__init__()

        # This makes it possible to use multiple instances of Switch
        global _count
        self._count = _count
        _count += 1
        self._topic = mqtt_topic or _mqtt.getDeviceTopic("{!s}/{!s}".format(_component_name, self._count),
                                                         is_request=True)
        self._subscribe(self._topic, self.on_message)
        self._frn = friendly_name
        gc.collect()
        self.lock = config.Lock()  # in case switch activates a device that will need a while to finish
        self._c_on = Popen(command_on, expected_return_on, expected_execution_time_on, iterations, iter_delay)
        self._c_off = Popen(command_off, expected_return_off, expected_execution_time_off, iterations, iter_delay)

    async def on_message(self, topic, msg, retain):
        if self.lock.locked():
            return False
        async with self.lock:
            if msg in _mqtt.payload_on:
                r = await self._c_on.execute()
                if r is True:
                    return True
                else:
                    await _log.asyncLog("warn", "Got unexpected return: {!s}".format(r))
                    return False
            elif msg in _mqtt.payload_off:
                r = await self._c_off.execute()
                if r is True:
                    return True
                else:
                    await _log.asyncLog("warn", "Got unexpected return: {!s}".format(r))
                    return False
        return False  # will not publish the state "ON" to mqtt

    async def _discovery(self):
        name = "{!s}{!s}".format(_component_name, self._count)
        await self._publishDiscovery(_component_type, self._topic[:-4], name, DISCOVERY_SWITCH, self._frn)
        # note that _publishDiscovery does expect the state topic but we have the command topic stored.
