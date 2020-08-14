#!/usr/bin/env bash
cd ~/micropython/ports/esp8266
/usr/local/bin/esptool.py --port /dev/ttyS6 erase_flash