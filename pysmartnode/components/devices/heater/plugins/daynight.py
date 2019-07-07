''''
Created on 2018-09-25

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.heater.plugins.daynight
    component: Daynight
    constructor_args: {
        # HEATER: heaterObject    # optional, name of heater object registered before this component, defaults to the registered one
        # NIGHT_TIME_TOPIC: None  # optional, defaults to <home>/<device-id>/heater/night_time, after this time heater will change target temp to NIGHT_TEMP (only if rtc_sync is active)
        # DAY_TIME_TOPIC: None    # optional, defaults to <home>/<device-id>/heater/day_time, after this time heater will change target temp to DAY_TEMP (only if rtc_sync is active)
        # NIGHT_TEMP_TOPIC: None  # optional, defaults to <home>/<device-id>/heater/night_temp
        # DAY_TEMP_TOPIC: None    # optional, defaults to <home>/<device-id>/heater/day_temp
        # DAY_TEMP: 22            # optional, defaults to 22C, temperature during the day, changed by mqtt
        # NIGHT_TEMP: 16          # optional, defaults to FROST temperature of heater, temperature during night, changed by mqtt
    }
}
Adds support for setting a day and a night temperature and time. RTC_SYNC_ACTIVE needs to be enabled!
This plugin works completely independent of other modules and modes and will adapt the target temperature. 
Between switching times, the target_temperature can be freely changed.
Times have to be in the format HH:MM:SS and in 24h format, seconds are ignored and optional.

Does not support homeassistant discovery as homeassistant doesn't have a component for sending float values.
"""

__updated__ = "2019-06-04"
__version__ = "0.8"

from ..core import log, _mqtt, Heater, _heater
import time
from pysmartnode import config
from pysmartnode.utils.component import Component


class Daynight(Component):
    def __init__(self, HEATER: Heater = None, NIGHT_TIME_TOPIC=None, DAY_TIME_TOPIC=None,
                 DAY_TEMP=22, NIGHT_TEMP=None, DAY_TEMP_TOPIC=None, NIGHT_TEMP_TOPIC=None):
        super().__init__()
        if HEATER is None and _heater is None:
            raise TypeError("No heater unit registered yet")
        self._heater = HEATER or _heater
        self._heater.registerPlugin(self._daynight, "daynight")
        if not config.RTC_SYNC_ACTIVE:
            raise TypeError("Plugin 'daynight' does not work without RTC_SYNC_ACTIVE")
        self.__time_day = None
        self.__time_night = None
        self.__last_change = None  # False=night, True=day
        self.__temp_day = DAY_TEMP
        self.__temp_night = NIGHT_TEMP or self._heater.getFrostTemperature()
        self.NIGHT_TIME_TOPIC = NIGHT_TIME_TOPIC or _mqtt.getDeviceTopic("heater/night_time", True)
        self.DAY_TIME_TOPIC = DAY_TIME_TOPIC or _mqtt.getDeviceTopic("heater/day_time", True)
        self.NIGHT_TEMP_TOPIC = NIGHT_TEMP_TOPIC or _mqtt.getDeviceTopic("heater/night_temp", True)
        self.DAY_TEMP_TOPIC = DAY_TEMP_TOPIC or _mqtt.getDeviceTopic("heater/day_temp", True)
        self._subscribe(self.NIGHT_TIME_TOPIC, self._setNightTime)
        self._subscribe(self.DAY_TIME_TOPIC, self._setDayTime)
        self._subscribe(self.NIGHT_TEMP_TOPIC, self._setNightTemp)
        self._subscribe(self.DAY_TEMP_TOPIC, self._setDayTemp)

    async def _init(self):
        await log.asyncLog("info", "Heater plugin 'daynight' version {!s}".format(__version__))
        await super()._init()

    async def _daynight(self, heater, data):
        if self.__time_day is None or self.__time_night is None:
            log.debug("No daynight times set", local_only=True)
            return
        t = time.localtime()
        if t[3] * 60 + t[4] >= self.__time_night or t[3] * 60 + t[4] < self.__time_day:
            # night time
            if self.__last_change is None:
                if t[3] * 60 + t[4] - self.__time_night > heater.getInterval():
                    self.__last_change = False
                    # on reboot assume that it was already set otherweise target_temp will get changed
                else:
                    self.__last_change = True
                    # heater could have rebooted before change was done, therefore accept change within REACTION_TIME
            if self.__last_change is True:
                self.__last_change = False
                heater.setTargetTemp(self.__temp_night)
        else:
            # day time
            if self.__last_change is None:
                if t[3] * 60 + t[4] - self.__time_day > heater.getInterval():
                    self.__last_change = True
                    # on reboot assume that it was already set otherweise target_temp will get changed
                else:
                    self.__last_change = False
                    # heater could have rebooted before change was done, therefore accept change within REACTION_TIME
            if self.__last_change is False:
                self.__last_change = True
                heater.setTargetTemp(self.__temp_day)

    async def _setNightTime(self, topic, msg, retain):
        try:
            t = msg.split(":")
        except Exception as e:
            log.error(e)
            return False
        if len(t) < 2:
            log.error("Wrong time format, use HH:MM:SS")
            return False
        self.__time_night = int(t[0]) * 60 + int(t[1])
        return True

    async def _setDayTime(self, topic, msg, retain):
        try:
            t = msg.split(":")
        except Exception as e:
            log.error(e)
            return False
        if len(t) < 2:
            log.error("Wrong time format, use HH:MM:SS")
            return False
        self.__time_day = int(t[0]) * 60 + int(t[1])
        return True

    async def _setNightTemp(self, topic, msg, retain):
        try:
            msg = float(msg)
        except Exception as e:
            log.error("Can't convert remote temperature to float: {!s}".format(e))
            return
        self.__temp_night = msg
        return True

    async def _setDayTemp(self, topic, msg, retain):
        try:
            msg = float(msg)
        except Exception as e:
            log.error("Can't convert remote temperature to float: {!s}".format(e))
            return
        self.__temp_day = msg
        return True
