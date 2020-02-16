#!/usr/bin/env bash
./dockercontainer-mpy-esp32-cc/build_mpy.sh 1.12 clean def
./dockercontainer-mpy-esp32-cc/build_mpy.sh 1.12 clean spiram
./esp32_sync.sh
./esp32_remove_hints.sh
echo "ready for write image"