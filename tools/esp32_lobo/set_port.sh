#!/bin/bash
new_port='CONFIG_ESPTOOLPY_PORT='\""$1"\"
sed -i '/CONFIG_ESPTOOLPY_PORT=.*/c\'"$new_port" ~/MicroPython_ESP32_psRAM_LoBo/MicroPython_BUILD/sdkconfig
