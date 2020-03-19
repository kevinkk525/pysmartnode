# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-10 

__updated__ = "2020-03-19"
__version__ = "0.3"

# The discovery base should be a json string to keep the RAM requirement low and only need
# to use format to enter the dynamic values so that the string is only loaded into RAM once
# during the discovery method call.
# Defining every base sensor in this module instead of in every custom component reduces RAM
# requirements of modules that are not frozen to firmware.
# For more variables see: https://www.home-assistant.io/docs/mqtt/discovery/
DISCOVERY_BASE = '{{' \
                 '"~":"{!s}",' \
                 '"name":"{!s}",' \
                 '"stat_t":"~",' \
                 '"uniq_id":"{!s}_{!s}",' \
                 '{!s}' \
                 '{!s}' \
                 '"dev":{!s}' \
                 '}}'

DISCOVERY_AVAILABILITY = '"avty_t":"{!s}/{!s}/{!s}",'
#                 '"pl_avail":"online",' \
#                 '"pl_not_avail":"offline",' \
#                 standard values

DISCOVERY_SENSOR = '"dev_cla":"{!s}",' \
                   '"unit_of_meas":"{!s}",' \
                   '"val_tpl":"{!s}",'

DISCOVERY_TIMELAPSE = '"dev_cla":"timestamp",' \
                      '"ic":"mdi:timelapse",'

DISCOVERY_BINARY_SENSOR = '"dev_cla":"{!s}",'  # "pl_on":"ON", "pl_off":"OFF",' are default

DISCOVERY_SWITCH = '"cmd_t":"~/set",'  # '"stat_on":"ON","stat_off":"OFF",' are default

VALUE_TEMPLATE_JSON = "{{{{ value_json.{!s} }}}}"
VALUE_TEMPLATE_FLOAT = "{{ value|float }}"
VALUE_TEMPLATE_INT = "{{ value|int }}"
VALUE_TEMPLATE = "{{ value }}"

# By homeassistant supported sensor definitions to be used as device classes in discovery
# Sensors
SENSOR_BATTERY = 'battery'
SENSOR_HUMIDITY = 'humidity'
SENSOR_ILLUMINANCE = 'illuminance'
SENSOR_SIGNAL_STRENGTH = 'signal_strength'
SENSOR_TEMPERATURE = 'temperature'
SENSOR_POWER = 'power'
SENSOR_PRESSURE = 'pressure'
SENSOR_TIMESTAMP = 'timestamp'

# Binary sensors
SENSOR_BINARY_BATTERY = ' battery'
SENSOR_BINARY_COLD = 'cold'
SENSOR_BINARY_CONNECTIVITY = 'connectivity'
SENSOR_BINARY_DOOR = 'door'
SENSOR_BINARY_GARAGE_DOOR = 'garage_door'
SENSOR_BINARY_GAS = 'gas'
SENSOR_BINARY_HEAT = 'heat'
SENSOR_BINARY_LIGHT = 'light'
SENSOR_BINARY_LOCK = 'lock'
SENSOR_BINARY_MOISTURE = 'moisture'
SENSOR_BINARY_MOTION = 'motion'
SENSOR_BINARY_MOVING = 'moving'
SENSOR_BINARY_OCCUPANCY = 'occupancy'
SENSOR_BINARY_OPENING = 'opening'
SENSOR_BINARY_PLUG = 'plug'
SENSOR_BINARY_POWER = 'power'
SENSOR_BINARY_PRESENCE = 'presence'
SENSOR_BINARY_PROBLEM = 'problem'
SENSOR_BINARY_SAFETY = 'safety'
SENSOR_BINARY_SMOKE = 'smoke'
SENSOR_BINARY_SOUND = 'sound'
SENSOR_BINARY_VIBRATION = 'vibration'
SENSOR_BINARY_WINDOW = 'window'
