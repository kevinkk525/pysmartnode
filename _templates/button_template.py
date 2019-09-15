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

__updated__ = "2019-09-14"
__version__ = "0.2"

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
    def __init__(self, mqtt_topic=None, friendly_name=None):
        # This makes it possible to use multiple instances of Button. It is needed for every default value.
        global _count
        self._count = _count
        _count += 1
        # mqtt_topic can be adapted otherwise a default mqtt_topic will be generated if None is passed
        super().__init__(COMPONENT_NAME, mqtt_topic, instance_name=None, wait_for_lock=False)
        self._frn = friendly_name
        # With a button there is no self._off() so if the device needs to be shut off at start,
        # launch a new coroutine.

    async def _init(self):
        # in this case not even needed as no additional init is being done.
        # You can remove this if you don't add additional code.

        # if you need to shut down/initialize the button before any networking, it can be done
        # before super()._init() or in __init__().
        await super()._init()
        # Don't use this coroutine to start code not related to mqtt or networking as it might
        # never be executed if the device can't get connected to wifi or mqtt but you might want
        # your device to work regardless of network status.

    #####################
    # Change this method according to your device.
    #####################
    async def _on(self):
        """Turn device on."""
        pass
        # no return needed because of single-shot action. If turning device on fails, it should be handled in the method
    #####################
