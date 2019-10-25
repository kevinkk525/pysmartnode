from sys import platform

###
# Uncomment optional configurations to change their default value.
# See pysmartnode/config_base.py for more configuration options.
###


# Required custom configuration
WIFI_SSID = "SSID"  # optional on esp8266 if it has been connected once
WIFI_PASSPHRASE = "PASSPHRASE"  # optional on esp8266 if it has been connected once
MQTT_HOST = "BROKER-IP"
MQTT_PORT = 1883
MQTT_USER = ""  # optional if no authentication needed
MQTT_PASSWORD = ""  # optional if no authentication needed

###
# Optional configuration
###
# MQTT_KEEPALIVE = const(120)
# MQTT_HOME = "home"
# MQTT_AVAILABILITY_SUBTOPIC = "available"  # will be generated to MQTT_HOME/<device-id>/MQTT_AVAILABILITY_SUBTOPIC
# MQTT_DISCOVERY_PREFIX = "homeassistant"
# MQTT_DISCOVERY_ENABLED = True
# MQTT_RECEIVE_CONFIG = True
###
# RECEIVE_CONFIG: Only use if you run the "SmartServer" in your environment which
# sends the configuration of a device over mqtt
# If you do not run it, you have to configure the components locally on each microcontroller
###

# WIFI_LED = None  # set a pin number to have the wifi state displayed by a blinking led. Useful for devices like sonoff
# WIFI_LED_ACTIVE_HIGH = True  # if led is on when output is low, change to False

# WEBREPL_ACTIVE = False  # If you want to have the webrepl active. Configures and starts it automatically.
# WEBREPL_PASSWORD = ""

if platform == "esp32" or platform == "esp8266":
    RTC_TIMEZONE_OFFSET = 2  # offset from GMT timezone as ntptime on esp8266 does not support timezones

# 10min, Interval sensors send a new value if not specified by specific configuration
# INTERVAL_SEND_SENSOR = const(600)

###
# Name of the device
##
# DEVICE_NAME = None
###
# set to a unique device name otherwise the id will be used.
# This is relevant for homeassistant mqtt autodiscovery so the device gets
# recognized by its device_name instead of the id.
# It is also used with the unix port instead of the unique chip id (which is not available
# on the unix port) and it therefore has to be UNIQUE in your network or
# it will result in problems.
###
