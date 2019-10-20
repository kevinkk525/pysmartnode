#!/usr/bin/env bash
cd ~/micropython/ports/esp8266
~/.local/bin/esptool.py --port /dev/ttyS3 erase_flash