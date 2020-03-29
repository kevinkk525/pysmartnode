# Author: Kevin Köck
# Copyright Kevin Köck 2020 Released under the MIT license
# Created on 2020-03-04

"""
example config:
{
    package: .switches.generic_switch
    component: GenSwitch
    constructor_args: {
        # mqtt_topic: null    # optional, defaults to <mqtt_home>/<device_id>/Switch<_unit_index>/set
        # friendly_name: null # optional, friendly name shown in homeassistant gui with mqtt discovery
        # discover: true      # optional, if false no discovery message for homeassistant will be sent.
    }
}
This generic switch does absolutely nothing except publishing its state and receiving state changes.
Can be used to represent (for example) the long-press state of a physical button.
"""

__updated__ = "2020-03-04"
__version__ = "1.0"

from pysmartnode import config
from pysmartnode.utils.component.switch import ComponentSwitch

COMPONENT_NAME = "GenericSwitch"

_mqtt = config.getMQTT()
_unit_index = -1


class GenSwitch(ComponentSwitch):
    def __init__(self, mqtt_topic=None, friendly_name=None, discover=True):
        global _unit_index
        _unit_index += 1
        initial_state = False
        super().__init__(COMPONENT_NAME, __version__, _unit_index, mqtt_topic, instance_name=None,
                         wait_for_lock=True, discover=discover, friendly_name=friendly_name,
                         initial_state=initial_state)

    @staticmethod
    async def _on():
        """Turn device on."""
        return True  # return True when turning device on was successful.

    @staticmethod
    async def _off():
        """Turn device off. """
        return True  # return True when turning device off was successful.
