#!/usr/bin/env bash
./tools/esp8266/esp8266_sync.sh
./tools/esp8266/esp8266_build.sh
./tools/esp8266/esp8266_flash.sh
./tools/esp8266/esp8266_initialize.sh
echo "Done"
