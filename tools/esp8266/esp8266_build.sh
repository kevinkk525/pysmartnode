#!/usr/bin/env bash
cd ~/micropython/ports/esp8266
export PATH=/home/kevin/esp-open-sdk/xtensa-lx106-elf/bin:$PATH
make clean BOARD=pysmartnode_4M
make BOARD=pysmartnode_4M -j12
