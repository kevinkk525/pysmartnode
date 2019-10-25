#!/usr/bin/env bash
cd ~/micropython/ports/esp8266/modules
rsync -av --prune-empty-dirs --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/kevin/ws_cloud/Programme Python/WNodePython/pysmartnode/" ./pysmartnode/ --delete
rsync -av --prune-empty-dirs --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/kevin/ws_cloud/Programme Python/WNodePython/_testing/" ./_testing/ --delete
rsync -av --prune-empty-dirs  --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/kevin/ws_cloud/Programme Python/WNodePython/external_modules/" ./
#rsync -av "/home/kevin/ws_cloud/Programme Python/WNodePython/config.py" ./
#rsync -av "/home/kevin/ws_cloud/Programme Python/WNodePython/main.py" ./
#rsync -av "/home/kevin/ws_cloud/Programme Python/WNodePython/boot.py" ./
# now using filesystem on the esp8266 so not needed to freeze these