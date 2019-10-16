# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-10-12

__updated__ = "2019-10-16"
__version__ = "0.2"

from pysmartnode.components.devices.climate import BaseMode
from .definitions import ACTION_OFF, MODE_OFF, CURRENT_ACTION


class off(BaseMode):
    # def __init__(self, climate):

    # async def _init(self):

    async def trigger(self, climate, current_temp):
        """Triggered whenever the situation is evaluated again"""
        if climate.heating_unit.state() is False and climate.state[CURRENT_ACTION] == ACTION_OFF:
            return True
        if await climate.heating_unit.off():
            climate.state[CURRENT_ACTION] = ACTION_OFF
            return True
        return False

    async def activate(self, climate):
        """Triggered whenever the mode changes and this mode has been activated"""
        return True  # no init needed

    async def deactivate(self, climate):
        """Triggered whenever the mode changes and this mode has been deactivated"""
        return True  # no deinit needed

    def __str__(self):
        """Name of the mode, has to be the same as the classname/module"""
        return MODE_OFF
