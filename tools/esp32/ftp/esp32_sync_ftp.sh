#!/bin/bash
HOST="192.168.178.70"
USER=""
PASS=""
TARGETFOLDER="/pysmartnode"
SOURCEFOLDER="/mnt/r/WNodePython/pysmartnode/"

lftp -f "
open $HOST
user $USER $PASS
lcd $SOURCEFOLDER
mirror --reverse --delete --verbose $SOURCEFOLDER $TARGETFOLDER
bye
"
echo "Done"