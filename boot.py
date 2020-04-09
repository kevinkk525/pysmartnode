# This file is executed on every boot (including wake-boot from deepsleep)
# import esp
# esp.osdebug(0)
import gc

# import webrepl
# webrepl.start()
gc.collect()


def reload(mod):
    import sys
    mod_name = mod.__name__
    del sys.modules[mod_name]
    return __import__(mod_name)


import uos
import machine

uos.dupterm(machine.UART(0, 115200), 1)
