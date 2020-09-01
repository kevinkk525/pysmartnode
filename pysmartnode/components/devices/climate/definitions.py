# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2019-10-12 

__updated__ = "2020-08-31"
__version__ = "0.4"

CLIMATE_DISCOVERY = '{{' \
                    '"~":"{!s}/state",' \
                    '"name":"{!s}",' \
                    '{!s}' \
                    '"uniq_id":"{!s}_{!s}",' \
                    '"curr_temp_t":"{!s}",' \
                    '"curr_temp_tpl":"{!s}",' \
                    '"mode_stat_t":"~",' \
                    '"mode_stat_tpl":"{{{{ value_json.mode }}}}",' \
                    '"mode_cmd_t":"~m/set",' \
                    '"act_t":"~",' \
                    '"act_tpl":"{{{{ value_json.action }}}}",' \
                    '"temp_step":{!s},' \
                    '"min_temp":{!s},' \
                    '"max_temp":{!s},' \
                    '"modes":{!s},' \
                    '"away_mode_cmd_t":"~aw/set",' \
                    '"away_mode_stat_t":"~",' \
                    '"away_mode_stat_tpl":"{{{{ value_json.away }}}}",' \
                    '{!s}' \
                    '"dev":{!s}' \
                    '}}'

CLIMATE_DISCOVERY_HILOW = '"temp_lo_cmd_t":"~tl/set",' \
                          '"temp_lo_stat_t":"~",' \
                          '"temp_lo_stat_tpl":"{{ value_json.c_temp_l }}",' \
                          '"temp_hi_cmd_t":"~th/set",' \
                          '"temp_hi_stat_t":"~",' \
                          '"temp_hi_stat_tpl":"{{ value_json.c_temp_h }}",'

CLIMATE_DISCOVERY_STEMP = '"temp_cmd_t":"~t/set",' \
                          '"temp_stat_t":"~",' \
                          '"temp_stat_tpl":"{{ value_json.c_temp }}",'

# IMPLEMENTED MODES
MODE_OFF = "off"
MODE_HEAT = "heat"
MODES_SUPPORTED = [MODE_OFF, MODE_HEAT]

# ACTION STATES
ACTION_OFF = "off"
ACTION_HEATING = "heating"
ACTION_COOLING = "cooling"
ACTION_DRYING = "drying"
ACTION_IDLE = "idle"
ACTION_FAN = "fan"
ACTIONS = [ACTION_OFF, ACTION_HEATING, ACTION_COOLING, ACTION_DRYING, ACTION_IDLE, ACTION_FAN]

# AWAY MODES
AWAY_OFF = "OFF"
AWAY_ON = "ON"

# CLIMATE STATE ATTRIBUTES
# when changing values make sure to change the discovery message values accordingly
CURRENT_TEMPERATURE_LOW = "c_temp_l"
CURRENT_TEMPERATURE_HIGH = "c_temp_h"
CURRENT_TEMPERATURE_SINGLE = "c_temp"
AWAY_MODE_STATE = "away"
STORAGE_AWAY_TEMPERATURE_LOW = "_a_temp_l"
STORAGE_AWAY_TEMPERATURE_HIGH = "_a_temp_h"
STORAGE_TEMPERATURE_LOW = "_temp_l"
STORAGE_TEMPERATURE_HIGH = "_temp_h"
CURRENT_MODE = "mode"
CURRENT_ACTION = "action"
