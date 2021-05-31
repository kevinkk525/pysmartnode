import machine
from sys import platform


def UART(id=None, rx=None, tx=None, baudrate=9600, **kwargs):
    if id is None:
        return machine.UART(rx, tx, baudrate=baudrate, **kwargs)
    else:
        return machine.UART(id, baudrate=baudrate, **kwargs)
