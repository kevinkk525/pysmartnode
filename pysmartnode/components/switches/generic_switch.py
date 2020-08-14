# Author: Kevin Köck
# Copyright Kevin Köck 2020 Released under the MIT license
# Created on 2020-03-04

"""
example config:
{
    package: .switches.generic_switch
    component: GenSwitch
    constructor_args: {}
}
This generic switch does absolutely nothing except publishing its state and receiving state changes.
Can be used to represent (for example) the long-press state of a physical button.
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

__updated__ = "2020-04-03"
__version__ = "1.11"

from pysmartnode import config
from pysmartnode.utils.component.switch import ComponentSwitch

COMPONENT_NAME = "GenericSwitch"

_mqtt = config.getMQTT()
_unit_index = -1


class GenSwitch(ComponentSwitch):
    def __init__(self, **kwargs):
        global _unit_index
        _unit_index += 1
        initial_state = False
        super().__init__(COMPONENT_NAME, __version__, _unit_index, wait_for_lock=True,
                         initial_state=initial_state, **kwargs)

    @staticmethod
    async def _on():
        """Turn device on."""
        return True  # return True when turning device on was successful.

    @staticmethod
    async def _off():
        """Turn device off. """
        return True  # return True when turning device off was successful.
