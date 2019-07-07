#!/usr/bin/env bash
cd ~/micropython/ports/esp8266
esptool.py --port /dev/ttyS3 erase_flash
