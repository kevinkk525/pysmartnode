#!/usr/bin/env bash
cd ~/micropython/ports/esp8266
/usr/local/bin/esptool.py --port /dev/ttyS7 erase_flash
