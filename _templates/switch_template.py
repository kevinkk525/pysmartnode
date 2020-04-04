# Author: Kevin Köck
# Copyright Kevin Köck 2017-2020 Released under the MIT license
# Created on 2017-10-31

"""
example config:
{
    package: <package_path>
    component: Switch
    constructor_args: {
        # mqtt_topic: null    # optional, defaults to <mqtt_home>/<device_id>/Switch<_unit_index>/set
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

__updated__ = "2020-04-03"
__version__ = "1.91"

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
    def __init__(self, mqtt_topic=None, friendly_name=None, **kwargs):
        # This makes it possible to use multiple instances of Button.
        # It is needed for every default value for mqtt.
        # Initialize before super()__init__(...) to not pass the wrong value.
        global _unit_index
        _unit_index += 1

        # mqtt_topic and friendly_name can be removed from the constructor if not initialized
        # differently by this module if not given by the user. If removed from the constructor,
        # also remove it from super().__init__(...)!
        # example:
        friendly_name = friendly_name or "mySwitch_name_friendly_{!s}".format(_unit_index)

        ###
        # set the initial state otherwise it will be "None" (unknown) and the first request
        # will set it accordingly.
        initial_state = None
        # should be False/True if can read your devices state on startup or know the state because
        # you initialize a pin in a certain state.
        ###

        # mqtt_topic can be adapted otherwise a default mqtt_topic will be generated if not
        # provided by user configuration.
        # friendly_name can be adapted, otherwise it will be unconfigured (which is ok too).
        super().__init__(COMPONENT_NAME, __version__, _unit_index,
                         friendly_name=friendly_name, mqtt_topic=mqtt_topic,
                         # remove friendly_name and mqtt_topic if removed from constructor
                         wait_for_lock=True, initial_state=initial_state, **kwargs)

        # If the device needs extra code, launch a new coroutine.

    #####################
    # Change these methods according to your device.
    #####################
    async def _on(self) -> bool:
        """Turn device on."""
        return True  # return True when turning device on was successful.

    async def _off(self) -> bool:
        """Turn device off. """
        return True  # return True when turning device off was successful.
    #####################
