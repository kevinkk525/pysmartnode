'''
Created on 2018-08-13

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.heater.JunkersZWR183
    component: Heater
    constructor_args: { 
        PIN: D5                     # pin that controls the heater
        TEMP_SENSOR: htu            # name of a temperature sensor in COMPONENTS, needs to provide an async temperature() or tempHumid() coroutine
        REACTION_TIME: 900          # how often heater reacts to temperature changes in internal mode
        HYSTERESIS_LOW: 0.25        # the theater will start heating below target temperature minus hysteresis
        HYSTERESIS_HIGH: 0.25       # the theater will stop heating above target temperature plus hysteresis
        SHUTDOWN_CYCLES: 2          # amount of cycles (in reaction time) after which the heater will shut down if target+hysteris_high reached
        START_CYCLES: 2             # amount of cycles (in reaction time) after which the heater will start heating if temp<(target-hysteresis_low); prevents short spikes from starting up the heater (opening a window)
        # FROST_TEMP: 16            # optional, defaults to 16C, will try to keep temperature above this temperature, no matter what mode/settings are used
        # SHUTDOWN_TEMP: 29         # optional, defaults to 29C, shuts heater down if that temperature is reached no matter what mode/settings are used
        # TARGET_TEMP: 22           # optional, defaults to 22C, target temperature for startup only, data published to TARGET_TEMP_TOPIC will be used afterwards
        # STATUS_TOPIC: None        # optional, defaults to <home>/<device-id>/heater/status, publishes current state of heater (running, error, ...)
        # POWER_TOPIC: None         # optional, defaults to <home>/<device-id>/heater/power, for requesting and publishing the current power level of the heater (if supported)
        # TARGET_TEMP_TOPIC: None   # optional, defaults to <home>/<device-id>/heater/temp, for changing the target temperature
        # MODE_TOPIC: None          # optional, defaults to <home>/<device-id>/heater/mode, for setting heater to internal mode, fully remotely controlled, etc
    }
}
inherits everything from Core and just adds the correct hardware (pin on/off) and remoteControl mode
"""

__updated__ = "2018-09-28"
__version__ = "0.4"

from .core import Heater as Core, log
from .plugins.daynight import daynight
from .hardware.pin import pin


async def Heater(PIN, **kwargs):
    print("inside heater")
    heater = Core(**kwargs)
    await pin(heater, PIN, INVERTED=True)
    await daynight(heater)
    await log.asyncLog("info", "JunkersZWR18-3 created, version {!s}".format(__version__))
    return heater
