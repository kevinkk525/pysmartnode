HOST="192.168.178.160"
USER="micro"
PASS="python"
TARGETFOLDER="/flash/pysmartnode"
SOURCEFOLDER="/mnt/b/WNodePython/pysmartnode/"

lftp -f "
open $HOST
user $USER $PASS
lcd $SOURCEFOLDER
mirror --reverse --delete --verbose $SOURCEFOLDER $TARGETFOLDER
bye
"
echo "Done"