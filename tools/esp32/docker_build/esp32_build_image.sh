#!/usr/bin/env bash
#./dockercontainer-mpy-esp32-cc/build_mpy.sh 1.12 mk def
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 dockercontainer-mpy-esp32-cc/mpy-firmware-1.12-def.bin # Todo: Flashmode -fm dio/qio is possible, --baud 115200 is possible