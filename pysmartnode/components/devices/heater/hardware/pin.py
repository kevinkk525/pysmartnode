'''
Created on 2018-08-13

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.heater.hardware.pin
    component: pin
    constructor_args: {
        HEATER: heaterObject    # name of heater object registered before this component
        PIN: D5 # pin that controls the heater
    }
}
"""

__updated__ = "2018-10-05"
__version__ = "0.4"

from ..core import log
from pysmartnode.components.machine.pin import Pin
import machine

_pin = None
_inverted = False


# not converting to a Component subclass as it doesn't use any mqtt.

async def pin(HEATER, PIN, INVERTED=False):
    global _pin
    global _inverted
    _inverted = INVERTED
    _pin = Pin(PIN, machine.Pin.OUT)
    await log.asyncLog("info", "Heater hardware PIN version {!s}".format(__version__))
    HEATER.registerHardware(_setHeaterPower)
    await _setHeaterPower(0)  # initialize heater as shut down


async def _setHeaterPower(power):
    """ Adapt this function to fit required hardware"""
    log.debug("setting power to {!s}".format(0 if power == 0 else 100), local_only=True)
    if power == 0:
        _pin.value(_inverted)
    else:
        _pin.value(not _inverted)
    return True
