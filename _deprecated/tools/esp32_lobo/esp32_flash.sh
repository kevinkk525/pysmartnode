PORT="$1"
cd ~/MicroPython_ESP32_psRAM_LoBo/MicroPython_BUILD/
#./BUILD.sh erase -p $PORT
./BUILD.sh -a 1536 flash -p $PORT
#mpfshell -o ttyUSB0 --reset -n
