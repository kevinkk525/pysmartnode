#!/usr/bin/env bash
sudo apt-get install git wget libncurses-dev flex bison gperf python python-pip python-setuptools python-serial python-click python-cryptography python-future python-pyparsing python-pyelftools cmake ninja-build ccache
pip3 install pyserial pyparsing esptool rshell
cd ~/
git clone https://github.com/micropython/micropython.git
cd micropython
git submodule update --init
cd ports/esp32
hash=$(make | grep "Supported git hash:")
hash=${hash:20}
cd ~/
git clone https://github.com/espressif/esp-idf.git
cd esp-idf
git checkout $hash
git submodule update --init
cd ..
mkdir esp
cd esp
wget https://dl.espressif.com/dl/xtensa-esp32-elf-linux64-1.22.0-80-g6c4433a-5.2.0.tar.gz
tar -zxvf xtensa-esp32-elf-linux64-1.22.0-80-g6c4433a-5.2.0.tar.gz
export PATH="$HOME/esp/xtensa-esp32-elf/bin:$PATH"
cd ..
cd micropython/ports/esp32
echo '''ESPIDF = $(HOME)'/esp-idf'
#PORT = /dev/ttyUSB0
#FLASH_MODE = qio
#FLASH_SIZE = 4MB
#CROSS_COMPILE = xtensa-esp32-elf-

include Makefile''' > makefile
cd ..
cd ..
git submodule update --init
make -C mpy-cross
cd ports/esp32
make PYTHON=python2 -j12