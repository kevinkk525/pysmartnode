'''
Created on 31.10.2017

@author: Kevin Köck
'''

"""
example config:
{
    package: <package_path>
    component: Switch
    constructor_args: {
        # mqtt_topic: null     #optional, defaults to <mqtt_home>/<device_id>/Buzzer/set
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
"""

__updated__ = "2019-06-03"
__version__ = "1.1"

import gc
from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.component import Component, DISCOVERY_SWITCH

####################
# choose a component name that will be used for logging (not in leightweight_log),
# a default mqtt topic that can be changed by received or local component configuration
# as well as for the component name in homeassistant.
_component_name = "Switch"
# define the type of the component according to the homeassistant specifications
_component_type = "switch"
####################

_mqtt = config.getMQTT()
_log = logging.getLogger(_component_name)

gc.collect()

_count = 0


class Switch(Component):
    def __init__(self, mqtt_topic=None, friendly_name=None):
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

    async def _init(self):
        # in this case not even needed as no additional init is being done.
        await super()._init()

    async def on_message(self, topic, msg, retain):
        if self.lock.locked():
            return False
        async with self.lock:
            if msg in _mqtt.payload_on:
                await _mqtt.publish(self._topic[:-4], "ON", qos=1, retain=True)  # if a long action is being done
                return True  # if only a short action is being done. "ON" will be published automatically.
                # Don't use both instructions
            elif msg in _mqtt.payload_off:
                await _mqtt.publish(self._topic[:-4], "OFF", qos=1, retain=True)  # if a long action is being done
                return True  # if only a short action is being done. "OFF" will be published automatically.
                # Don't use both instructions
            else:
                await _log.asyncLog("error", "Payload {!s} not supported".format(msg))
        return False  # will not publish the state "ON" to mqtt

    async def _discovery(self):
        name = "{!s}{!s}".format(_component_name, self._count)
        await self._publishDiscovery(_component_type, self._topic[:-4], name, DISCOVERY_SWITCH, self._frn)
        # note that _publishDiscovery does expect the state topic but we have the command topic stored.
