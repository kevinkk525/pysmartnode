#!/usr/bin/env bash
esptool.py --port /dev/ttyS7 --baud 115200 write_flash --flash_size=1MB -fm dout 0x0 /home/kevin/micropython/ports/esp8266/build-pysmartnode_1M/firmware-combined.bin
