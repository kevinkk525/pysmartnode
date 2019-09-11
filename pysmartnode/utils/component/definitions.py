# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-10 

__updated__ = "2019-09-10"
__version__ = "0.1"

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
                 '"avty_t":"{!s}/{!s}/status",' \
                 '"uniq_id":"{!s}_{!s}",' \
                 '{!s}' \
                 '"dev":{!s}' \
                 '}}'
#                 '"pl_avail":"online",' \
#                 '"pl_not_avail":"offline",' \
#                 standard values

DISCOVERY_BASE_NO_AVAIL = '{{' \
                          '"~":"{!s}",' \
                          '"name":"{!s}",' \
                          '"stat_t":"~",' \
                          '"uniq_id":"{!s}_{!s}",' \
                          '{!s}' \
                          '"dev":{!s}' \
                          '}}'

DISCOVERY_SENSOR = '"dev_cla":"{!s}",' \
                   '"unit_of_meas":"{!s}",' \
                   '"val_tpl":"{!s}",'

TIMELAPSE_TYPE = '"dev_cla":"timestamp",' \
                 '"ic":"mdi:timelapse",'

DISCOVERY_BINARY_SENSOR = '"dev_cla":"{!s}",'  # "pl_on":"ON", "pl_off":"OFF",' are default

DISCOVERY_SWITCH = '"cmd_t":"~/set",'  # '"stat_on":"ON","stat_off":"OFF",' are default
