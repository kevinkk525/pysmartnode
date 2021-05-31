# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2019-10-22 

__updated__ = "2021-05-24"

from sys import platform
from micropython import const

# Required custom configuration
WIFI_SSID = ""
WIFI_PASSPHRASE = ""
MQTT_HOST = ""
MQTT_PORT = const(1883)
MQTT_USER = ""
MQTT_PASSWORD = ""

# Optional configuration
MQTT_KEEPALIVE = const(120)
MQTT_HOME = "home"
MQTT_AVAILABILITY_SUBTOPIC = "available"  # will be generated to MQTT_HOME/<device-id>/MQTT_AVAILABILITY_SUBTOPIC
MQTT_DISCOVERY_PREFIX = "homeassistant"
MQTT_DISCOVERY_ENABLED = True
MQTT_RECEIVE_CONFIG = False
# RECEIVE_CONFIG: Only use if you run the "SmartServer" in your environment which
# sends the configuration of a device over mqtt
# If you do not run it, you have to configure the components locally on each microcontroller
# using a components.py file
MQTT_TYPE = const(1)  # 1: direct, 0: IOT implementation (not working at the moment, use direct)
MQTT_MAX_CONCURRENT_EXECUTIONS = -1
# MAX_CONCURRENT_EXECUTIONS: Can be used to restrict the amount of concurrently executed mqtt
# messages to prevent message spam to crash the device.
# However there is no safety against crashing the device with very long messages.

WIFI_LED = None  # set a pin number to have the wifi state displayed by a blinking led. Useful for devices like sonoff
WIFI_LED_ACTIVE_HIGH = True  # if led is on when output is low, change to False

WEBREPL_ACTIVE = False  # If you want to have the webrepl active. Configures and starts it automatically.
WEBREPL_PASSWORD = ""

RTC_SYNC_ACTIVE = True  # uses ~600B additional RAM on esp8266
RTC_TIMEZONE_OFFSET = 1  # offset from GMT timezone as ntptime does not support timezones
RTC_DAYLIGHT_SAVINGS = False  # will add +1 hour to timezone during summer time.

FTP_ACTIVE = False
FTP_THREADED = False

MAIN_LOOP_THREADED = False # run main loop in a thread. Can be used on PYBD as a workaround to have a working webrepl

WATCHDOG_LEVEL = 0 # 0 = disabled, 1 = Software Watchdog using Timers, 2 = Hardware Watchdog (if available on platform)

if platform == "esp32":
    FTP_ACTIVE = True
elif platform == "pyboard":
    FTP_ACTIVE = True
    RTC_SYNC_ACTIVE = False # bug in pybd results in permenanet connection loss after syncing time once..
    PIN3V3_ENABLED = True
elif platform == "esp8266":
    LIGTWEIGHT_LOG = False  # uses a smaller class for logging on esp8266 omitting module names, saves ~500Bytes
    WATCHDOG_LEVEL = 1  # uses ~700B of RAM, started with timeout=2xMQTT_KEEPALIVE, use if you experience outages
    WIFI_SLEEP_MODE = 0  # WIFI_NONE_SLEEP = 0, WIFI_LIGHT_SLEEP = 1, WIFI_MODEM_SLEEP = 2; changed to 0 for increased stability. Standard is 2. Integrated into mqtt_as.
elif platform == "linux":
    RTC_SYNC_ACTIVE = True  # This should always be True unless your system doesn't have access to the internet or sync the time

INTERVAL_SENSOR_PUBLISH = const(600)  # publish sensor readings every 10 minutes by default
INTERVAL_SENSOR_READ = const(120)  # read sensor every 2 minutes by default

# Device specific configurations:
#
# Name of the device
DEVICE_NAME = None
# set to a unique device name otherwise the id will be used.
# This is relevant for homeassistant mqtt autodiscovery so the device gets
# recognized by its device_name instead of the id.
# It is also used with the unix port instead of the unique chip id (which is not available
# on the unix port) and it therefore has to be UNIQUE in your network or
# it will result in problems.

# Does not need to be changed normally
DEBUG = False
DEBUG_STOP_AFTER_EXCEPTION = False

from config import *
# config.py will overwrite configuration values defined here.
# This way only changes need to be put into config.py and the default values will
# remain in config_base which is frozen bytecode and won't take up RAM.
# Also makes adding new options easier as their default will be part of the firmware.
