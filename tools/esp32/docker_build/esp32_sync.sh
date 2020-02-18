#!/bin/bash

echo "Cur dir: $(pwd)"

# shellcheck disable=SC2164
cd ~/PycharmProjects/upy-nodes/tools/esp32/docker_build/dockercontainer-mpy-esp32-cc/mods # Todo: change Dirpath


rsync -av --prune-empty-dirs --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/tholo/PycharmProjects/upy-nodes/pysmartnode/" ./pysmartnode/ --delete
rsync -av --prune-empty-dirs --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/tholo/PycharmProjects/upy-nodes/_testing/" ./_testing/ --delete
rsync -av --prune-empty-dirs  --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/tholo/PycharmProjects/upy-nodes/external_modules/" ./

cd ~/PycharmProjects/upy-nodes/tools/esp32/docker_build/dockercontainer-mpy-esp32-cc/1.12/def/mpscripts
rsync -av "/home/tholo/PycharmProjects/upy-nodes/config.py" ./
rsync -av "/home/tholo/PycharmProjects/upy-nodes/main.py" ./
rsync -av "/home/tholo/PycharmProjects/upy-nodes/boot.py" ./

