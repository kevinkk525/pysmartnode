# Author: Kevin Köck
# Copyright Kevin Köck 2020 Released under the MIT license
# Created on 2020-03-31 

"""
example config:
{
    package: .switches.433mhz
    component: Switch433Mhz
    constructor_args: {
        pin: 21                 # pin number or object
        file: "filename"        # filename where the captured sequences are stored. Has to be uploaded manually!
        name_on: "on_a"         # name of the sequence for turning the device on
        name_off: "off_a"      # name of the sequence for turning the device off
        # reps: 5               # optional, amount of times a frame is being sent
    }
}
Control 433Mhz devices (e.g. power sockets) with a cheap 433Mhz transmitter.
Uses the excellent library from Peter Hinch: https://github.com/peterhinch/micropython_remote
For this to work you need to have sequences captured and stores on the device.
How to do that is described in his repository.
Note: This component only works on the devices supported by Peter Hinch's library!
(esp32, pyboards but not esp8266).
Be careful with "reps", the amount of repitions as this currently uses a lot of RAM.

NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

__updated__ = "2020-04-03"
__version__ = "0.2"

from pysmartnode import config
from pysmartnode.utils.component.switch import ComponentSwitch
from pysmartnode.libraries.micropython_remote.tx import TX
from pysmartnode.components.machine.pin import Pin
import json
import uasyncio as asyncio
import machine

####################
COMPONENT_NAME = "433MhzRemote"
####################

_mqtt = config.getMQTT()
_unit_index = -1
_tx: TX = None
_remotes = {}
_lock = asyncio.Lock()


class Switch433Mhz(ComponentSwitch):
    def __init__(self, pin, file: str, name_on: str, name_off: str, reps: int = 5, **kwargs):
        global _unit_index
        _unit_index += 1
        global _tx
        if file not in _remotes and _tx is None:
            pin = Pin(pin, machine.Pin.OUT)
            _tx = TX(pin, file, reps)
            _remotes[file] = _tx._data
        elif file not in _remotes:
            with open(file, 'r') as f:
                rem = json.load(f)
            # exceptions are forwarded to the caller
            _remotes[file] = rem
        if name_on not in _remotes[file]:
            raise AttributeError("name_on {!r} not in file {!s}".format(name_on, file))
        if name_off not in _remotes[file]:
            raise AttributeError("name_off {!r} not in file {!s}".format(name_off, file))

        super().__init__(COMPONENT_NAME, __version__, _unit_index, wait_for_lock=True,
                         initial_state=None, **kwargs)
        # Unknown initial state. Should be sorted by retained state topic

        self._reps = reps
        self._file = file
        self._len_on = int(sum(_remotes[self._file][name_on]) * 1.1 / 1000)
        self._len_off = int(sum(_remotes[self._file][name_off]) * 1.1 / 1000)
        self._name_on = name_on
        self._name_off = name_off

        # one lock for all switches, overrides lock created by the base class
        self._lock = _lock

    #####################
    # Change these methods according to your device.
    #####################
    async def _on(self):
        """Turn device on."""
        _tx._data = _remotes[self._file]
        reps = _tx._reps
        _tx._reps = self._reps
        _tx(self._name_on)
        await asyncio.sleep_ms(self._len_on * self._reps)
        _tx._reps = reps
        # wait until transmission is done so lock only gets released afterwards because
        # only one transmission can occur at a time.
        return True

    async def _off(self):
        """Turn device off. """
        _tx._data = _remotes[self._file]
        reps = _tx._reps
        _tx._reps = self._reps
        _tx(self._name_off)
        await asyncio.sleep_ms(self._len_off * self._reps)
        _tx._reps = reps
        # wait until transmission is done so lock only gets released afterwards because
        # only one transmission can occur at a time.
        return True
        #####################
