CLEAN="$1"
cd ~/MicroPython_ESP32_psRAM_LoBo/MicroPython_BUILD/
if [ "$CLEAN" = "clean" ]
then
	git pull
	./BUILD.sh clean
fi
#./BUILD.sh menuconfig < mncfg_exit.txt
./BUILD.sh -v -j10
#./BUILD -a 2048 flash
#mpfshell -o ttyUSB0 --reset -n
