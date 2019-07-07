#!/bin/bash
cd "/home/kevin/ws_cloud/Programme Python/WNodePython/"
#mpfshell -o ttyS9 -n -c "put main.py"
#mpfshell -o ttyS9 -n -c "put config.py"
#mpfshell -o ttyS9 -n -c "put boot.py"
rshell -p /dev/ttyS3 "cp config.py /pyboard/;cp boot.py /pyboard/;cp main.py /pyboard/"
