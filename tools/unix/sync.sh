#!/usr/bin/env bash
cd ~/.micropython/lib
rsync -av --prune-empty-dirs --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/kevin/ws_cloud/Programme Python/WNodePython/pysmartnode/" ./pysmartnode/ --delete
rsync -av --prune-empty-dirs --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/kevin/ws_cloud/Programme Python/WNodePython/_testing/" ./_testing/ --delete
rsync -av --prune-empty-dirs --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/kevin/ws_cloud/Programme Python/WNodePython/external_modules/" ./
