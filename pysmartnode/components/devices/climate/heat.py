# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-10-12 

__updated__ = "2019-10-25"
__version__ = "0.4"

from pysmartnode.components.devices.climate import BaseMode
from .definitions import ACTION_HEATING, ACTION_IDLE, MODE_HEAT, CURRENT_ACTION, \
    CURRENT_TEMPERATURE_HIGH, CURRENT_TEMPERATURE_LOW


class heat(BaseMode):
    def __init__(self, climate):
        super().__init__(climate)
        self._last_state = False

    # async def _init(self):

    async def trigger(self, climate, current_temp):
        """Triggered whenever the situation is evaluated again"""
        if current_temp is None:
            await climate.log.asyncLog("warn", "No temperature", timeout=2, await_connection=False)
            # keep heater state is no temp is available.
            # Makes it possible to use external button to switch heater state manually
            # in case temperature sensor is broken or network unavailable.
            # Will be overwritten on next trigger though if temperature is available.
            return True
        if current_temp > climate.state[CURRENT_TEMPERATURE_HIGH] and self._last_state is True:
            # target temperature reached
            if await climate.heating_unit.off():
                climate.state[CURRENT_ACTION] = ACTION_IDLE
                self._last_state = False
                return True
            else:
                climate.log.error("Couldn't deactivate heater")
                return False
        elif current_temp < climate.state[CURRENT_TEMPERATURE_LOW] and self._last_state is False:
            # start heating
            if await climate.heating_unit.on():
                climate.state[CURRENT_ACTION] = ACTION_HEATING
                self._last_state = True
                return True
            else:
                climate.log.error("Couldn't activate heater")
                return False
        else:
            # temperature between target temperatures high and low
            # set action and state in case the state is retained or changed manually by button
            if climate.heating_unit.state() is True and \
                    climate.state[CURRENT_ACTION] != ACTION_HEATING:
                climate.state[CURRENT_ACTION] = ACTION_HEATING
                self._last_state = True
            elif climate.heating_unit.state() is False and \
                    climate.state[CURRENT_ACTION] != ACTION_IDLE:
                climate.state[CURRENT_ACTION] = ACTION_IDLE
                self._last_state = False

    async def activate(self, climate):
        """Triggered whenever the mode changes and this mode has been activated"""
        self._last_state = climate.heating_unit.state()
        return True

    async def deactivate(self, climate):
        """Triggered whenever the mode changes and this mode has been deactivated"""
        return True  # no deinit needed

    def __str__(self):
        """Name of the mode, has to be the same as the classname/module"""
        return MODE_HEAT
