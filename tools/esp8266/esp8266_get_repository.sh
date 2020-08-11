#!/usr/bin/env bash
sudo apt install make unrar-free autoconf automake libtool gcc g++ gperf \
    flex bison texinfo gawk ncurses-dev libexpat-dev python-dev python python3-serial \
    sed git unzip bash help2man wget bzip2
sudo apt install python3-dev python3-pip libtool-bin
pip3 install rshell esptool
cd ~/
git clone --recursive https://github.com/pfalcon/esp-open-sdk.git
cd esp-open-sdk
curl https://bootstrap.pypa.io/get-pip.py --output get-pip.py
sudo python2 get-pip.py
pip install pyserial
sed -i 's/GNU bash, version (3\.[1-9]|4)/GNU bash, version ([0-9\.]+)/' ~/esp-open-sdk/crosstool-NG/configure.ac
make STANDALONE=y
export PATH=/home/kevin/esp-open-sdk/xtensa-lx106-elf/bin:$PATH
cd ~/
git clone https://github.com/micropython/micropython.git
cd micropython
git submodule update --init
make -C mpy-cross
cd ports/esp8266
make axtls
sed -i 's/irom0_0_seg :  org = 0x40209000, len = 0x8f000/irom0_0_seg :  org = 0x40209000, len = 0xc7000/' ~/micropython/ports/esp8266/boards/esp8266.ld
make -j12
