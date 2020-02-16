#!/bin/bash

echo "Cur dir: $(pwd)"

# shellcheck disable=SC2164
cd ~/PycharmProjects/py-node/tools/esp32/dockercontainer-mpy-esp32-cc/mods # Todo: change Dirpath

#rsync -av "/home/tholo/PycharmProjects/py-node/pysmartnode" ./ --delete --exclude=*.sh --exclude=LICENSE --exclude=.gitmodules --exclude=*.ino --exclude=__pycache__ --exclude=.git --exclude=.gitignore --exclude=.project --exclude=.pydevproject --exclude=*.mpy --exclude=*.md --exclude=*.bin --exclude=*.h --exclude=*.c --exclude=*.cpp
#rsync -av "/home/tholo/PycharmProjects/py-node/_testing" ./ --delete --include=*.py --exclude=*.sh --exclude=__pycache__ --exclude=.git --exclude=.gitignore --exclude=.project --exclude=.pydevproject --exclude=*.mpy --exclude=*.md --exclude=*.bin --exclude=*.h --exclude=*.c --exclude=*.cpp
#rsync -av "/home/tholo/PycharmProjects/py-node/external_modules/" ./ --delete --prune-empty-dirs --exclude=*.sh --exclude=LICENSE --exclude=.gitmodules --exclude=*.ino --exclude=*.egg-info --exclude=.git --exclude=.gitignore --exclude=.project --exclude=.pydevproject --exclude=*.mpy --exclude=*.md --exclude=*.bin --exclude=*.h --exclude=*.c --exclude=*.cpp
rsync -av --prune-empty-dirs --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/tholo/PycharmProjects/py-node/pysmartnode/" ./pysmartnode/ --delete
rsync -av --prune-empty-dirs --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/tholo/PycharmProjects/py-node/_testing/" ./_testing/ --delete
rsync -av --prune-empty-dirs  --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/tholo/PycharmProjects/py-node/external_modules/" ./

cd ~/PycharmProjects/py-node/tools/esp32/dockercontainer-mpy-esp32-cc/1.12/def/mpscripts
rsync -av "/home/tholo/PycharmProjects/py-node/config.py" ./
rsync -av "/home/tholo/PycharmProjects/py-node/main.py" ./
rsync -av "/home/tholo/PycharmProjects/py-node/boot.py" ./

cd ~/PycharmProjects/py-node/tools/esp32/dockercontainer-mpy-esp32-cc/1.12/spiram/mpscripts
rsync -av "/home/tholo/PycharmProjects/py-node/config.py" ./
rsync -av "/home/tholo/PycharmProjects/py-node/main.py" ./
rsync -av "/home/tholo/PycharmProjects/py-node/boot.py" ./
