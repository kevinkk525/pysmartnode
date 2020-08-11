#!/usr/bin/env bash
cd ~/micropython/ports/esp8266
export PATH=/home/kevin/esp-open-sdk/xtensa-lx106-elf/bin:$PATH
make BOARD=pysmartnode_4M PORT=/dev/ttyS4 FLASH_MODE=qio FLASH_SIZE=32m BAUDRATE=115200 deploy
