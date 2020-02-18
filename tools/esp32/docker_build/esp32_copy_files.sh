#!/usr/bin/env bash
cd /home/tholo/PycharmProjects/upy-nodes
ampy -p /dev/ttyUSB0 put main.py
ampy -p /dev/ttyUSB0 put config.py
ampy -p /dev/ttyUSB0 put boot.py
echo "files are ready"