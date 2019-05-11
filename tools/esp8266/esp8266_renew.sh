#!/usr/bin/env bash
cd tools/esp8266
./esp8266_sync.sh
./esp8266_build.sh
./esp8266_flash.sh 
#./esp8266_initialize.sh
echo "Done"
