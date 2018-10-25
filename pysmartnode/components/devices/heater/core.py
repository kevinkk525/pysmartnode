'''
Created on 2018-08-10

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.heater.core
    component: Heater
    constructor_args: { 
        TEMP_SENSOR: htu            # name of a temperature sensor in COMPONENTS, needs to provide an async temperature() or tempHumid() coroutine
        REACTION_TIME: 900          # how often heater reacts to temperature changes
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
"""

"""
Short documentation:
- method for actually controlling the heater has to be implemented in subclass or by registering hardware by function
- FROST_TEMP and SHUTDOWN_TEMP are only checked with internal temperature sensor
- therefore if internal sensor fails, no mode or plugin will be checked and heater shuts down (after 3 failed readings)
- heater reacts to target temperature or mode change immediately
- heater reacts to temperature change every REACTION_TIME seconds and waits xxx_CYCLES before starting/shutting down heater
"""

__updated__ = "2018-10-02"
__version__ = "0.8"

from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
from pysmartnode.utils.event import Event
import gc
import time

_mqtt = config.getMQTT()
log = logging.getLogger("Heater")  # not _log as submodules import it
gc.collect()


class Heater:
    def __init__(self, TEMP_SENSOR, REACTION_TIME, HYSTERESIS_LOW, HYSTERESIS_HIGH,
                 SHUTDOWN_CYCLES, START_CYCLES, FROST_TEMP=16, SHUTDOWN_TEMP=29, TARGET_TEMP=22,
                 TARGET_TEMP_TOPIC=None, STATUS_TOPIC=None, POWER_TOPIC=None, MODE_TOPIC=None):
        # self.__sensor = config.getComponent(TEMP_SENSOR)
        self.__sensor = TEMP_SENSOR  # registerComponents already gets the component
        if self.__sensor is None:
            log.critical("Can't initialize heater as temperature sensor {!r} does not exist!".format(TEMP_SENSOR))
            raise TypeError("temperature sensor {!r} does not exist".format(TEMP_SENSOR))
        if hasattr(self.__sensor, "tempHumid") is False and hasattr(self.__sensor, "temperature") is False:
            log.critical(
                "Can't initialize heater as temperature sensor {!r} has no supported coroutine for getting temperature".format(
                    TEMP_SENSOR))
            raise TypeError("temperature sensor {!r} does not have supported API")
        self.__interval = REACTION_TIME
        self.__hysteresis_low = HYSTERESIS_LOW
        self.__hysteresis_high = HYSTERESIS_HIGH
        self.__shutdown_cycles = SHUTDOWN_CYCLES
        self.__start_cycles = START_CYCLES
        self.__frost_temp = FROST_TEMP
        self.__shutdown_temp = SHUTDOWN_TEMP
        self.__target_temp = TARGET_TEMP
        self.__status_topic = STATUS_TOPIC or _mqtt.getDeviceTopic("heater/status")
        self.__power_topic = POWER_TOPIC or _mqtt.getDeviceTopic("heater/power")
        self.__mode_topic = MODE_TOPIC or _mqtt.getDeviceTopic("heater/mode")
        self.__target_temp_topic = TARGET_TEMP_TOPIC or _mqtt.getDeviceTopic("heater/temp")
        ######
        # internal variables
        ######
        self.__active_mode = "INTERNAL"
        self.__modes = {"INTERNAL": self.__modeInternal}
        self.__plugins = {}
        self.__target_power = 0
        self.__event = Event()
        self.__cycles_target_reached = -2  # will immediately react to current temperature
        self.__loop_started = False
        self.__timer_time = 0  # has to be object variable so that _watch can update it too
        self.__last_error = None
        self.__setHeaterPower = None  # coro of registered hardware
        self.__initializeHardware = None  # initialization coro if hardware requires it
        #####
        asyncio.get_event_loop().create_task(self._initialize())

    async def _updateMQTTStatus(self):
        await _mqtt.publish(self.__power_topic, self.__target_power, True, qos=1)
        if self.__last_error is None:
            if self.__target_power == 0:
                await _mqtt.publish(self.__status_topic, "OFF", True, qos=1)
            else:
                await _mqtt.publish(self.__status_topic, "ON", True, qos=1)
        else:
            await _mqtt.publish(self.__status_topic, self.__last_error, True, qos=1)
        await _mqtt.publish(self.__target_temp_topic, self.__target_temp, True, qos=1)
        await _mqtt.publish(self.__mode_topic, self.__active_mode, True, qos=1)

    def registerHardware(self, set_power, hardware_init=None):
        self.__setHeaterPower = set_power
        self.__initializeHardware = hardware_init

    def registerPlugin(self, coro, name):
        if coro is None:
            raise TypeError("Can't register plugin of type None")
        log.debug("Registering plugin {!s}".format(name), local_only=True)
        if coro not in self.__plugins:
            self.__plugins[name] = coro
            return True
        else:
            log.warn("Plugin {!s} already registered")
        return False

    def getInterval(self):
        return self.__interval

    def getHysteresisLow(self):
        return self.__hysteresis_low

    def getHysteresisHigh(self):
        return self.__hysteresis_high

    def getShutdownCycles(self):
        return self.__shutdown_cycles

    def getStartCycles(self):
        return self.__start_cycles

    def getFrostTemperature(self):
        return self.__frost_temp

    def getShutdownTemperature(self):
        return self.__shutdown_temp

    def getTargetTemp(self):
        return self.__target_temp

    def setTargetTemp(self, temp):
        log.debug("Set target temp to {!s}".format(temp), local_only=True)
        self.__target_temp = temp
        if self.__loop_started:
            self.__cycles_target_reached = -2  # makes heater react to temp change immediately

    def getStatusTopic(self):
        return self.__status_topic

    def getPowerTopic(self):
        return self.__power_topic

    def getModeTopic(self):
        return self.__mode_topic

    def getActiveMode(self):
        return self.__active_mode

    def setEvent(self):
        self.__event.set()

    def getTargetPower(self):
        return self.__target_power

    def setLastError(self, error):
        self.__last_error = error

    def getLastError(self):
        return self.__last_error

    async def _initialize(self):
        await log.asyncLog("info", "Heater Core version {!s}".format(__version__))
        await _mqtt.subscribe(self.__mode_topic + "/set", self.setMode, qos=1)
        await _mqtt.subscribe(self.__target_temp_topic + "/set", self._requestTemp, qos=1)
        if self.__initializeHardware is not None:
            await self.__initializeHardware()
        asyncio.get_event_loop().create_task(self._timer())
        asyncio.get_event_loop().create_task(self._watch())
        gc.collect()

    def addMode(self, mode, coro):
        self.__modes[mode] = coro

    def hasStarted(self):
        return self.__loop_started

    async def setMode(self, topic, msg, retain):
        if msg not in self.__modes:
            log.error("Mode {!r} not supported".format(msg))
            return None
        if self.__last_error == "FROST":
            log.warn("Can't change mode to {!r} as temperature is below frost")
            return None
        if self.__loop_started:
            # wait for execution of cycle to end
            while self.__event.is_set():
                await asyncio.sleep_ms(50)
        log.debug("setMode {!s}".format(msg), local_only=True)
        self.__active_mode = msg
        self.__cycles_target_reached = -2 if retain else 0
        if self.__loop_started:
            self.__event.set()
        await _mqtt.publish(self.__mode_topic[:-4], msg, retain=True, qos=1)
        gc.collect()
        return True

    async def _requestTemp(self, topic, msg, retain):
        if self.__loop_started:
            while self.__event.is_set():
                await asyncio.sleep_ms(50)
        try:
            temp = float(msg)
        except:
            log.error("Error converting requested temp to float: {!r}".format(msg))
            return None
        self.__target_temp = temp
        log.debug("requestTemp {!s}".format(temp), local_only=True)
        # await _mqtt.publish(self.__target_temp_topic[:-4], self.__target_temp, retain=True, qos=1)
        if self.__loop_started:
            self.__cycles_target_reached = -2  # makes heater react to temp change immediately
            self.__event.set()
        return True

    async def _timer(self):
        self.__timer_time = time.ticks_ms()
        while True:
            while (time.ticks_ms() - self.__timer_time) < (self.__interval * 1000):
                await asyncio.sleep(1)
            self.__timer_time = time.ticks_ms()  # will also be set by _watch when resetting event
            log.debug("Reaction time reached", local_only=True)
            self.__event.set()

    async def _getTemperature(self):
        if hasattr(self.__sensor, "tempHumid"):
            return (await self.__sensor.tempHumid())["temperature"]
        elif hasattr(self.__sensor, "temperature"):
            return await self.__sensor.temperature()
        else:
            raise TypeError("No supported temperature sensor API")

    async def _watch(self):
        await asyncio.sleep(10)  # gives time to get retained values for targetTemp,Mode,Power,etc; and register plugins
        await self.__setHeaterPower(self.__target_power)
        # otherwise heater power would be floating or depending on how the hardware initializes
        self.__loop_started = True
        temp_reading_errors = 0
        frost_cycles = 0
        while True:
            current_temp = await self._getTemperature()
            log.debug("CurrentTemp: {!s}".format(current_temp), local_only=True)
            do_update = True
            if current_temp is False or current_temp is None:
                if self.__last_error != "NO_TEMP":
                    log.error("heater could not get current temperature, try {!s}".format(temp_reading_errors))
                    temp_reading_errors += 1
                    if temp_reading_errors >= 3:
                        log.critical("heater could not get temperature 3 times, shutting down heater")
                        self.__last_error = "NO_TEMP"
                        await self._setHeaterPower(0)
                self.__timer_time = time.ticks_ms() - self.__interval / 2 * 1000  # wait only 1/2 reaction time
                do_update = False
            elif current_temp < self.__frost_temp and self.__target_power < 100:
                if self.__last_error != "FROST":
                    if self.__active_mode != "INTERNAL":
                        self.__active_mode = "INTERNAL"  # if different mode was active, it has failed
                    await self._setHeaterPower(100)
                    self.__last_error = "FROST"
                else:
                    frost_cycles += 1
                    if frost_cycles >= 3:
                        log.critical("Heater can't raise temperature above frost")
                temp_reading_errors = 0
                do_update = False
            elif current_temp > self.__shutdown_temp:
                if self.__last_error != "TOO_HOT":
                    if self.__active_mode != "INTERNAL":
                        self.__active_mode = "INTERNAL"  # if different mode was active, it has failed (or summer)
                    log.error("heater shutdown due to too high temperature of {!r}°C".format(current_temp))
                    await self._setHeaterPower(0)
                    self.__last_error = "TOO_HOT"
                # could be summer
                temp_reading_errors = 0
                frost_cycles = 0
                do_update = False
            else:
                frost_cycles = 0
                temp_reading_errors = 0
            if do_update:
                last_error = self.__last_error
                data = {"current_temp": current_temp}
                for plugin in self.__plugins:
                    try:
                        await self.__plugins[plugin](self, data)
                    except Exception as e:
                        log.error("Plugin {!s} failed: {}".format(plugin, e))
                await self.__modes[self.__active_mode](self, data)
                if self.__last_error == last_error:
                    # reset error if not set by the mode coroutine
                    # as error is no longer valid if execution of mode was successful
                    self.__last_error = None
            await self._updateMQTTStatus()
            await self.__event
            self.__event.clear()
            self.__timer_time = time.ticks_ms()
        # in case of shutdown, code currently not reached anyways
        # await self._setHeaterPower(0)

    async def __modeInternal(self, heater, data):
        log.debug(data, local_only=True)
        current_temp = data["current_temp"]
        power = None
        target_power = self.__target_power
        if target_power > 0 and current_temp > self.__target_temp + self.__hysteresis_high:
            self.__cycles_target_reached += 1
            if self.__cycles_target_reached >= self.__shutdown_cycles or self.__cycles_target_reached == -1:
                power = 0
                self.__cycles_target_reached = 0
        elif target_power == 0 and current_temp < self.__target_temp - self.__hysteresis_low:
            self.__cycles_target_reached += 1
            if self.__cycles_target_reached >= self.__start_cycles or self.__cycles_target_reached == -1:
                power = 100
                self.__cycles_target_reached = 0
        else:
            self.__cycles_target_reached = 0
            return
            # temperature in between; will keep 100% if rising and 0% if falling.
            # nothing to do. Could improve this by adding a timer checking if temp is really rising and warn otherwise
        log.debug("cycles_target_reached: {!s}".format(self.__cycles_target_reached), local_only=True)
        if power is None:
            return
        await self._setHeaterPower(power)

    async def _setHeaterPower(self, power):
        if self.__setHeaterPower is None:
            log.error("No hardware registered to control heater")
            await _mqtt.publish(self.__status_topic, "ERR: NO HARDWARE", True, qos=1)
        else:
            if not await self.__setHeaterPower(power):
                log.error("Could not set heater power to {!s}%, shutting heater down".format(power))
                await self.__setHeaterPower(0)
                self.__last_error = "ERR: HARDWARE"
            else:
                self.__target_power = power
