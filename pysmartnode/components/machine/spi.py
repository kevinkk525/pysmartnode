from machine import SoftSPI as _SoftSPI, SPI as _SPI
from pysmartnode.components.machine.pin import Pin
from sys import platform


def SoftSPI(sck, mosi, miso, baudrate=8000000):
    return _SoftSPI(sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso),
                    baudrate=baudrate)  # Configure SPI - see note below


if platform == "esp8266":
    def SPI(id=1, baudrate=8000000, **kwargs):
        return _SPI(id, baudrate=baudrate, **kwargs)
else:
    def SPI(id, sck, mosi, miso, baudrate=8000000, **kwargs):
        return _SPI(id, sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso),
                    baudrate=baudrate, **kwargs)
