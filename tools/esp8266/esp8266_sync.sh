#!/usr/bin/env bash
cd ~/micropython/ports/esp8266/modules
rsync -av "/home/kevin/ws_cloud/Programme Python/WNodePython/pysmartnode/" ./pysmartnode/ --delete --exclude=__pycache__ --exclude=.git --exclude=.gitignore --exclude=.project --exclude=.pydevproject --exclude=*.mpy --exclude=*.md --exclude=*.bin
rsync -av "/home/kevin/ws_cloud/Programme Python/WNodePython/_testing/" ./_testing/ --delete --exclude=__pycache__ --exclude=.git --exclude=.gitignore --exclude=.project --exclude=.pydevproject --exclude=*.mpy --exclude=*.md --exclude=*.bin
rsync -av "/home/kevin/ws_cloud/Programme Python/WNodePython/external_modules/" ./ --exclude=*.egg-info --exclude=.git --exclude=.gitignore --exclude=.project --exclude=.pydevproject --exclude=*.mpy --exclude=*.md --exclude=*.bin
rsync -av "/home/kevin/ws_cloud/Programme Python/WNodePython/config.py" ./
rsync -av "/home/kevin/ws_cloud/Programme Python/WNodePython/main.py" ./
rsync -av "/home/kevin/ws_cloud/Programme Python/WNodePython/boot.py" ./
