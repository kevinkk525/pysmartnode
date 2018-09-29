''''
Created on 2018-09-25

@author: Kevin Köck
'''

"""
example config:
{
    package: .devices.heater.plugins.daynight
    component: daynight
    constructor_args: {
        HEATER: heaterObject      # name of heater object registered before this component
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
"""

__updated__ = "2018-09-29"
__version__ = "0.5"

from ..core import log, _mqtt
import time
from pysmartnode import config

__time_day = None
__time_night = None
__temp_day = None
__temp_night = None
__last_change = None  # False=night, True=day


async def _daynight(heater, data):
    if __time_day is None or __time_night is None:
        log.debug("No daynight times set", local_only=True)
        return
    global __last_change
    t = time.localtime()
    if t[3] * 60 + t[4] >= __time_night or t[3] * 60 + t[4] < __time_day:
        # night time
        if __last_change is None:
            __last_change = False  # on reboot assume that it was already set otherweise target_temp will get changed
        elif __last_change is True:
            __last_change = False
            heater.setTargetTemp(__temp_night)
    else:
        # day time
        if __last_change is None:
            __last_change = True  # on reboot assume that it was already set otherweise target_temp will get changed
        elif __last_change is False:
            __last_change = True
            heater.setTargetTemp(__temp_day)


async def _setNightTime(topic, msg, retain):
    try:
        t = msg.split(":")
    except Exception as e:
        log.error(e)
        return False
    if len(t) < 2:
        log.error("Wrong time format, use HH:MM:SS")
        return False
    global __time_night
    __time_night = int(t[0]) * 60 + int(t[1])
    return True


async def _setDayTime(topic, msg, retain):
    try:
        t = msg.split(":")
    except Exception as e:
        log.error(e)
        return False
    if len(t) < 2:
        log.error("Wrong time format, use HH:MM:SS")
        return False
    global __time_day
    __time_day = int(t[0]) * 60 + int(t[1])
    return True


async def _setNightTemp(topic, msg, retain):
    try:
        msg = float(msg)
    except Exception as e:
        log.error("Can't convert remote temperature to float: {!s}".format(e))
        return
    global __temp_night
    __temp_night = msg
    return True


async def _setDayTemp(topic, msg, retain):
    try:
        msg = float(msg)
    except Exception as e:
        log.error("Can't convert remote temperature to float: {!s}".format(e))
        return
    global __temp_day
    __temp_day = msg
    return True


async def daynight(HEATER, NIGHT_TIME_TOPIC=None, DAY_TIME_TOPIC=None, DAY_TEMP=22,
                   NIGHT_TEMP=None, DAY_TEMP_TOPIC=None, NIGHT_TEMP_TOPIC=None):
    HEATER.registerPlugin(_daynight, "daynight")
    if not config.RTC_SYNC_ACTIVE:
        raise TypeError("Plugin 'daynight' does not work without RTC_SYNC_ACTIVE")
    global __temp_day
    global __temp_night
    __temp_day = DAY_TEMP
    __temp_night = NIGHT_TEMP or HEATER.getFrostTemperature()
    NIGHT_TIME_TOPIC = NIGHT_TIME_TOPIC or _mqtt.getDeviceTopic("heater/night_time", True)
    DAY_TIME_TOPIC = DAY_TIME_TOPIC or _mqtt.getDeviceTopic("heater/day_time", True)
    NIGHT_TEMP_TOPIC = NIGHT_TEMP_TOPIC or _mqtt.getDeviceTopic("heater/night_temp", True)
    DAY_TEMP_TOPIC = DAY_TEMP_TOPIC or _mqtt.getDeviceTopic("heater/day_temp", True)
    await _mqtt.subscribe(NIGHT_TIME_TOPIC, _setNightTime, qos=1)
    await _mqtt.subscribe(DAY_TIME_TOPIC, _setDayTime, qos=1)
    await _mqtt.subscribe(NIGHT_TEMP_TOPIC, _setNightTemp, qos=1)
    await _mqtt.subscribe(DAY_TEMP_TOPIC, _setDayTemp, qos=1)
    await log.asyncLog("info", "Heater plugin 'daynight' version {!s}".format(__version__))
