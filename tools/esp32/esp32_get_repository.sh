#!/usr/bin/env bash
sudo apt-get install git wget libncurses-dev flex bison gperf python python-pip python-setuptools python-serial python-click python-cryptography python-future python-pyparsing python-pyelftools cmake ninja-build ccache
sudo apt-get install git wget libncurses-dev flex bison gperf python python-pip python-setuptools cmake ninja-build ccache libffi-dev libssl-dev
pip3 install pyserial 'pyparsing<2.4' esptool rshell
cd ~/
git clone https://github.com/micropython/micropython.git
cd micropython
git submodule update --init
cd ports/esp32
hash=$(make | grep "Supported git hash (v4.0) (experimental):")
hash=${hash:42}
cd ~/
git clone -b release/v4.0 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
git pull
git checkout $hash
git submodule update --init
./install.sh
. $HOME/esp-idf/export.sh
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