#!/bin/bash
cd "/home/kevin/ws_cloud/Programme Python/WNodePython/"
mpfshell -o ttyS4 -n -c "put main.py"
mpfshell -o ttyS4 -n -c "put config.py"
mpfshell -o ttyS4 -n -c "put boot.py"