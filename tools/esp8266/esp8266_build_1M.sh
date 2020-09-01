#!/usr/bin/env bash
cd ~/micropython/ports/esp8266
export PATH=/home/kevin/esp-open-sdk/xtensa-lx106-elf/bin:$PATH
make clean BOARD=pysmartnode_1M
make BOARD=pysmartnode_1M -j12
