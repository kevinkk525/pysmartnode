#!/usr/bin/env bash
./esp8266_sync.sh
#./esp8266_remove_hints.sh
./esp8266_build.sh
./esp8266_flash.sh
#./esp8266_initialize.sh
echo "Done"
