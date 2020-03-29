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
        # mqtt_topic: null    # optional, defaults to <mqtt_home>/<device_id>/Switch<_unit_index>/set
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
        # discover: true      # optional, if false no discovery message for homeassistant will be sent.
    }
}
"""

__updated__ = "2020-03-29"
__version__ = "1.9"

from pysmartnode import config
from pysmartnode.utils.component.switch import ComponentSwitch

####################
# choose a component name that will be used for logging (not in leightweight_log),
# the default mqtt topic that can be changed by received or local component configuration
# as well as for the component name in homeassistant.
COMPONENT_NAME = "Switch"
####################

_mqtt = config.getMQTT()
_unit_index = -1


class Switch(ComponentSwitch):
    def __init__(self, mqtt_topic=None, friendly_name=None, discover=True, **kwargs):
        # discover: boolean, if this component should publish its mqtt discovery.
        # This can be used to prevent combined Components from exposing underlying
        # hardware components like a power switch

        # This makes it possible to use multiple instances of Button.
        # It is needed for every default value for mqtt.
        # Initialize before super()__init__(...) to not pass the wrong value.
        global _unit_index
        _unit_index += 1

        ###
        # set the initial state otherwise it will be "None" (unknown) and the first request
        # will set it accordingly.
        initial_state = None
        # should be False/True if can read your devices state on startup or know the state because
        # you initialize a pin in a certain state.
        ###

        # mqtt_topic can be adapted otherwise a default mqtt_topic will be generated if None
        super().__init__(COMPONENT_NAME, __version__, _unit_index, mqtt_topic, instance_name=None,
                         wait_for_lock=True, discover=discover, friendly_name=friendly_name,
                         initial_state=initial_state, **kwargs)

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
