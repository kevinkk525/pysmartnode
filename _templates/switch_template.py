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

__updated__ = "2019-10-20"
__version__ = "1.6"

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
    def __init__(self, mqtt_topic=None, friendly_name=None, discover=True):
        # discover: boolean, if this component should publish its mqtt discovery.
        # This can be used to prevent combined Components from exposing underlying
        # hardware components like a power switch

        # This makes it possible to use multiple instances of Button.
        # It is needed for every default value.
        global _count
        self._count = _count
        _count += 1
        # mqtt_topic can be adapted otherwise a default mqtt_topic will
        # be generated if None is passed
        super().__init__(COMPONENT_NAME, __version__, mqtt_topic, instance_name=None,
                         wait_for_lock=True, discover=discover)
        self._frn = friendly_name
        ###
        # set the initial state otherwise it will be "None" (unknown).
        self._state = False
        # Might be that you can read your devices state on startup or know the state because
        # you initialize a pin in a certain state.
        ###
        # If the device needs extra code, launch a new coroutine.

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
