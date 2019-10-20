# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-10

"""
example config:
{
    package: <package_path>
    component: Button
    constructor_args: {
        # mqtt_topic: null     #optional, defaults to <mqtt_home>/<device_id>/Buzzer/set
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
"""

# A button is basically a switch with a single-shot action that deactivates itself afterwards.

__updated__ = "2019-10-20"
__version__ = "0.5"

from pysmartnode import config
from pysmartnode.utils.component.button import ComponentButton

####################
# choose a component name that will be used for logging (not in leightweight_log),
# the default mqtt topic that can be changed by received or local component configuration
# as well as for the component name in homeassistant.
COMPONENT_NAME = "Button"
####################

_mqtt = config.getMQTT()
_count = 0


class Button(ComponentButton):
    def __init__(self, mqtt_topic=None, friendly_name=None, discover=True):
        # discover: boolean, if this component should publish its mqtt discovery.
        # This can be used to prevent combined Components from exposing underlying
        # hardware components like a power switch

        # This makes it possible to use multiple instances of Button.
        # It is needed for every default value for mqtt.
        global _count
        self._count = _count
        _count += 1
        # mqtt_topic can be adapted otherwise a default mqtt_topic will be generated if None
        super().__init__(COMPONENT_NAME, __version__, mqtt_topic, instance_name=None,
                         wait_for_lock=False, discover=discover)
        self._frn = friendly_name
        self._state = False  # A button will always be False as it is single-shot,
        # unless you have a device with a long single-shot action. Then you might
        # be able to poll its current state.

        # If the device needs extra code, launch a new coroutine.

    #####################
    # Change this method according to your device.
    #####################
    async def _on(self):
        """Turn device on."""
        pass
        # no return needed because of single-shot action.
        # If turning device on fails, it should be handled inside this method

    #####################
