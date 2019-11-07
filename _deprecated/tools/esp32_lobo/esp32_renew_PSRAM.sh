CLEAN="$1"
cd esp32_lobo
#./esp32_sync.sh
esp32_build.sh #CLEAN
esp32_flash.sh /dev/ttyS4
#./esp32_initialize.sh
#./esp32_initialize.sh
#cd ~/MicroPython_ESP32_psRAM_LoBo/MicroPython_BUILD/
#./BUILD.sh monitor
echo "Done"
