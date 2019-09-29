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

__updated__ = "2019-09-29"
__version__ = "1.4"

from pysmartnode import config
from pysmartnode.utils.component.switch import ComponentSwitch

####################
# choose a component name that will be used for logging (not in leightweight_log),
# the default mqtt topic that can be changed by received or local component configuration
# as well as for the component name in homeassistant.
COMPONENT_NAME = "Switch"
####################

_mqtt = config.getMQTT()
_count = 0


class Switch(ComponentSwitch):
    def __init__(self, mqtt_topic=None, friendly_name=None):
        # This makes it possible to use multiple instances of Button.
        # It is needed for every default value.
        global _count
        self._count = _count
        _count += 1
        # mqtt_topic can be adapted otherwise a default mqtt_topic will
        # be generated if None is passed
        super().__init__(COMPONENT_NAME, __version__, mqtt_topic, instance_name=None,
                         wait_for_lock=True)
        self._frn = friendly_name
        # If the device needs extra code, launch a new coroutine.

    async def _init(self):
        # await self._off()
        # can be called if you want the device to shut down first before any networking
        await super()._init()

        # Don't use this coroutine to start code not related to mqtt or networking as it might
        # never be executed if the device can't get connected to wifi or mqtt but you might want
        # your device to work regardless of network status.

    #####################
    # Change these methods according to your device.
    #####################
    async def _on(self):
        """Turn device on."""
        return True  # return True when turning device on was successful.

    async def _off(self):
        """Turn device off. """
        return True  # return True when turning device off was successful.
    #####################
