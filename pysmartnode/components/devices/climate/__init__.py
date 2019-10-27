# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-10-10

"""
example config:
{
    package: .devices.climate
    component: Climate
    constructor_args: {
        temperature_sensor: "mysensor"  # temperature sensor name or object. can also be a remote sensor
        heating_unit: "myswitch"        # heating unit name or object. implemented as ComponentSwitch turning on/off the heating unit
        modes: ["off","heat"]           # all supported modes. cooling, auto and fan not implemented.
        # temp_step: 0.1                # temperature steps in homeassistant gui
        # precision: 0.1                # temperature sensor precision in homeassistant
        # min_temp: 16                  # optional, minimal possible target temp
        # max_temp: 28                  # optional, maximal possible target temp
        # temp_low: 20                  # optional, initial temperature low if no value saved by mqtt
        # temp_high: 21                 # optional, initial temperature high if no value saved by mqtt
        # away_temp_low: 16             # optional, initial away temperature low if no value saved by mqtt
        # away_temp_high: 17            # optional, initial away temperature high if no value saved by mqtt
        # disover: true                 # optional, send mqtt discovery
        # interval: 300            #optional, defaults to 300s, interval sensor checks situation. Should be >60s
        # friendly_name: null    # optional, friendly name shown in homeassistant gui with mqtt discovery
    }
}
Note: - mqtt broker is used to save the state between restarts using retained messages.
      - Temp_high/low supported since Homeassistant >100.3, before there were temp_high/low
        templates missing.

Not Implemented:
cooling_unit
fan_unit
"""

__updated__ = "2019-10-27"
__version__ = "0.6"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
from pysmartnode.utils.event import Event
import gc
import time
from pysmartnode.utils.component import Component
from pysmartnode.utils import sys_vars
import ujson
from .definitions import *

COMPONENT_NAME = "Climate"
_COMPONENT_TYPE = "climate"

_mqtt = config.getMQTT()
_log = logging.getLogger(COMPONENT_NAME)

gc.collect()

_count = 0


class BaseMode:
    """
    Base class for all modes
    """

    def __init__(self, climate):
        pass

    # async def _init(self):

    async def trigger(self, climate, current_temp):
        """Triggered whenever the situation is evaluated again"""
        raise NotImplementedError

    async def activate(self, climate):
        """Triggered whenever the mode changes and this mode has been activated"""
        raise NotImplementedError

    async def deactivate(self, climate):
        """Triggered whenever the mode changes and this mode has been deactivated"""
        raise NotImplementedError

    def __str__(self):
        """Name of the mode, has to be the same as the classname/module"""
        raise NotImplementedError


class Climate(Component):
    def __init__(self, temperature_sensor, heating_unit, modes: list, interval=300,
                 temp_step=0.1, min_temp=16, max_temp=28, temp_low=20, temp_high=21,
                 away_temp_low=16, away_temp_high=17,
                 friendly_name=None, discover=True):
        super().__init__(COMPONENT_NAME, __version__, discover)

        # This makes it possible to use multiple instances of MyComponent
        global _count
        self._count = _count
        _count += 1

        self._temp_step = temp_step
        self._min_temp = min_temp
        self._max_temp = max_temp
        if hasattr(temperature_sensor, "temperature") is False:
            raise TypeError("Temp sensor doesn't have coro temperature()")
        if isinstance(temperature_sensor, Component) is False:
            raise TypeError(
                "Temp sensor {!s} is not of instance Component".format(temperature_sensor))
        if isinstance(heating_unit, Component) is False:
            raise TypeError("heating_unit {!s} is not of instance Component".format(heating_unit))
        self.temp_sensor = temperature_sensor
        self.heating_unit = heating_unit
        self._modes = {}
        if "off" not in modes:
            modes.append("off")
        for mode in modes:
            if mode not in MODES_SUPPORTED:
                _log.error("Mode {!s} not supported".format(mode))
                modes.remove(mode)
            else:
                try:
                    mod = __import__("pysmartnode.components.devices.climate.{}".format(mode),
                                     globals(), locals(), [], 0)
                except ImportError as e:
                    _log.error("Mode {!s} not available: {!s}".format(mode, e))
                    continue
                if hasattr(mod, mode):
                    modeobj = getattr(mod, mode)
                else:
                    _log.error("Mode {!s} has no class {!r}".format(mode, mode))
                    continue
                try:
                    modeobj = modeobj(self)
                except Exception as e:
                    _log.error("Error creating mode {!s} object: {!s}".format(mode, e))
                    continue
                self._modes[mode] = modeobj
        self._frn = friendly_name
        self.state = {CURRENT_TEMPERATURE_HIGH:      temp_high,  # current temperature high
                      CURRENT_TEMPERATURE_LOW:       temp_low,  # current temperature low
                      AWAY_MODE_STATE:               AWAY_OFF,  # away mode "ON"/"OFF"
                      STORAGE_AWAY_TEMPERATURE_HIGH: away_temp_high,  # away temperature low
                      STORAGE_AWAY_TEMPERATURE_LOW:  away_temp_low,  # away temperature high
                      STORAGE_TEMPERATURE_HIGH:      temp_high,  # temperature high, storage value
                      STORAGE_TEMPERATURE_LOW:       temp_low,  # temperature low, storage value
                      CURRENT_MODE:                  str(self._modes["off"]),
                      CURRENT_ACTION:                ACTION_OFF}
        self.event = Event()
        self.lock = config.Lock()
        # every extneral change (like mode) that could break an ongoing trigger needs
        # to be protected by self.lock.
        self.log = _log
        gc.collect()

        self._mode_topic = _mqtt.getDeviceTopic(
            "{!s}{!s}/statem/set".format(COMPONENT_NAME, self._count))
        self._temp_low_topic = _mqtt.getDeviceTopic(
            "{!s}{!s}/statetl/set".format(COMPONENT_NAME, self._count))
        self._temp_high_topic = _mqtt.getDeviceTopic(
            "{!s}{!s}/stateth/set".format(COMPONENT_NAME, self._count))
        self._away_topic = _mqtt.getDeviceTopic(
            "{!s}{!s}/stateaw/set".format(COMPONENT_NAME, self._count))
        _mqtt.subscribeSync(self._mode_topic, self.changeMode, self)
        _mqtt.subscribeSync(self._temp_low_topic, self.changeTempLow, self)
        _mqtt.subscribeSync(self._temp_high_topic, self.changeTempHigh, self)
        _mqtt.subscribeSync(self._away_topic, self.changeAwayMode, self)

        self._restore_done = False
        asyncio.get_event_loop().create_task(self._loop(interval))

    async def _init_network(self):
        for mode in self._modes:
            if hasattr(mode, "_init"):
                await mode._init()
        gc.collect()
        await _mqtt.awaitSubscriptionsDone()  # wait until subscriptions are done
        # because received messages will take up RAM and the discovery message
        # of climate is very big and could easily fail if RAM is fragmented.
        gc.collect()
        await asyncio.sleep(1)
        gc.collect()
        await super()._init_network()
        # let discovery succeed first because it is a big message
        _mqtt.subscribeSync(
            _mqtt.getDeviceTopic("{!s}{!s}/state".format(COMPONENT_NAME, self._count)),
            self._restore, self)
        gc.collect()
        for _ in range(16):
            # get retained values
            if self._restore_done is True:
                break
            await asyncio.sleep_ms(250)
        if self._restore_done is False:
            await _mqtt.unsubscribe(
                _mqtt.getDeviceTopic("{!s}{!s}/state".format(COMPONENT_NAME, self._count)), self)
            self._restore_done = True
        await _mqtt.publish(
            _mqtt.getDeviceTopic("{!s}{!s}/state".format(COMPONENT_NAME, self._count)),
            self.state, qos=1, retain=True, timeout=4)

    async def _loop(self, interval):
        interval = interval * 1000
        t = time.ticks_ms()
        while self._restore_done is False and time.ticks_diff(time.ticks_ms(), t) < 30000:
            await asyncio.sleep(1)
            # wait for network to finish so the old state can be restored, or time out (30s)
        t = 0
        while True:
            while time.ticks_diff(time.ticks_ms(), t) < interval and not self.event.is_set():
                await asyncio.sleep_ms(100)
            if self.event.is_set():
                self.event.clear()
            # These publish methods will block at most 10 sec which should be fine for a HVAC unit
            async with self.lock:
                cur_temp = await self.temp_sensor.temperature(publish=True, timeout=5)
                try:
                    await self._modes[self.state[CURRENT_MODE]].trigger(self, cur_temp)
                except Exception as e:
                    _log.error(
                        "Error executing mode {!s}: {!s}".format(self.state[CURRENT_MODE], e))
                await _mqtt.publish(
                    _mqtt.getDeviceTopic("{!s}{!s}/state".format(COMPONENT_NAME, self._count)),
                    self.state, qos=1, retain=True, timeout=4)
            t = time.ticks_ms()

    async def _restore(self, topic, msg, retain):
        # used to restore the state after a restart since away temperature is different
        # but only one topic is used for away=False/True.
        await _mqtt.unsubscribe(
            _mqtt.getDeviceTopic("{!s}{!s}/state".format(COMPONENT_NAME, self._count)), self)
        mode = msg[CURRENT_MODE]
        del msg[CURRENT_MODE]
        del msg[CURRENT_ACTION]  # is going to be set after trigger()
        self.state.update(msg)
        try:
            await self.changeMode(topic, mode, retain)
        except AttributeError as e:
            _log.error(e)
        self._restore_done = True
        await asyncio.sleep(1)
        self.event.set()

    async def changeAwayMode(self, topic, msg, retain):
        if msg in _mqtt.payload_on:
            if self.state[AWAY_MODE_STATE] == AWAY_ON:
                return False  # no publish needed as done in _loop
            async with self.lock:
                self.state[AWAY_MODE_STATE] = AWAY_ON
                self.state[CURRENT_TEMPERATURE_HIGH] = self.state[STORAGE_AWAY_TEMPERATURE_HIGH]
                self.state[CURRENT_TEMPERATURE_LOW] = self.state[STORAGE_AWAY_TEMPERATURE_LOW]
                self.event.set()
                return False  # no publish needed as done in _loop
        elif msg in _mqtt.payload_off:
            if self.state[AWAY_MODE_STATE] == AWAY_OFF:
                return False  # no publish needed as done in _loop
            async with self.lock:
                self.state[AWAY_MODE_STATE] = AWAY_OFF
                self.state[CURRENT_TEMPERATURE_HIGH] = self.state[STORAGE_TEMPERATURE_HIGH]
                self.state[CURRENT_TEMPERATURE_LOW] = self.state[STORAGE_TEMPERATURE_LOW]
                self.event.set()
                return False  # no publish needed as done in _loop
        else:
            raise TypeError("Unsupported payload {!s}".format(msg))

    async def changeMode(self, topic, msg, retain):
        if msg not in self._modes:
            raise AttributeError("Mode {!s} not supported".format(msg))
        if msg == self.state[CURRENT_MODE]:
            return False  # no publish needed as done in _loop  # mode already active
        async with self.lock:
            mode = self._modes[msg]
            if await self._modes[self.state[CURRENT_MODE]].deactivate(self):
                if await mode.activate(self):
                    self.state[CURRENT_MODE] = msg
                    self.event.set()
                    return False  # no publish needed as done in _loop
                else:
                    self.state[CURRENT_MODE] = MODE_OFF
                    await self._modes[MODE_OFF].activate()
                    self.event.set()
                    return False
            else:
                return False

    async def changeTempHigh(self, topic, msg, retain):
        msg = float(msg)
        if msg > self._max_temp:
            raise ValueError("Can't set temp to {!s}, max temp is {!s}".format(msg,
                                                                               self._max_temp))
        if self.state[CURRENT_TEMPERATURE_HIGH] == msg:
            return False  # already set to requested temperature, prevents unneeded event & publish
        self.state[CURRENT_TEMPERATURE_HIGH] = msg
        if self.state[AWAY_MODE_STATE] == AWAY_ON:
            self.state[STORAGE_AWAY_TEMPERATURE_HIGH] = msg
        else:
            self.state[STORAGE_TEMPERATURE_HIGH] = msg
        self.event.set()
        return False

    async def changeTempLow(self, topic, msg, retain):
        msg = float(msg)
        if msg < self._min_temp:
            raise ValueError("Can't set temp to {!s}, min temp is {!s}".format(msg,
                                                                               self._min_temp))
        if self.state[CURRENT_TEMPERATURE_LOW] == msg:
            return False  # already set to requested temperature, prevents unneeded event & publish
        self.state[CURRENT_TEMPERATURE_LOW] = msg
        if self.state[AWAY_MODE_STATE] == AWAY_ON:
            self.state[STORAGE_AWAY_TEMPERATURE_LOW] = msg
        else:
            self.state[STORAGE_TEMPERATURE_LOW] = msg
        self.event.set()
        return False

    async def _discovery(self):
        name = "{!s}{!s}".format(COMPONENT_NAME, self._count)
        base_topic = _mqtt.getRealTopic(_mqtt.getDeviceTopic(name))
        modes = ujson.dumps([str(mode) for mode in self._modes])
        gc.collect()
        sens = CLIMATE_DISCOVERY.format(base_topic, self._frn or name, self._composeAvailability(),
                                        sys_vars.getDeviceID(), name,  # unique_id
                                        _mqtt.getRealTopic(self.temp_sensor.temperatureTopic()),
                                        # current_temp_topic
                                        self.temp_sensor.temperatureTemplate(),
                                        # cur_temp_template
                                        self._temp_step, self._min_temp, self._max_temp,
                                        modes, sys_vars.getDeviceDiscovery())
        gc.collect()
        topic = Component._getDiscoveryTopic(_COMPONENT_TYPE, name)
        await _mqtt.publish(topic, sens, qos=1, retain=True)
