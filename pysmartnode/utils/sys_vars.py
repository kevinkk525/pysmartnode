# Author: Kevin Köck
# Copyright Kevin Köck 2018-2020 Released under the MIT license
# Created on 2018-02-02

__updated__ = "2019-10-22"

import os
import ubinascii
from sys import platform

DISCOVERY_DEVICE_BASE = '{{' \
                        '"ids":"{!s}",' \
                        '"sw":"pysmartnode {!s}",' \
                        '"mf":"{!s}",' \
                        '"mdl":"{!s}",' \
                        '"name": "{!s}"' \
                        '{!s}' \
                        '}}'


def getDeviceType():
    if platform == "linux":
        return os.name
    return os.uname().sysname


def getDeviceID():
    if platform == "linux":
        from pysmartnode import config
        return config.DEVICE_NAME
    import machine
    return ubinascii.hexlify(machine.unique_id()).decode()


def hasFilesystem():
    if platform == "linux":
        return True  # assume working filesystem
    return not os.statvfs("")[0] == 0


def getDeviceDiscovery():
    from pysmartnode import config
    mf = "espressif" if platform in ("esp8266", "esp32", "esp32_LoBo") else "None"
    if platform != "linux":
        import network
        s = network.WLAN(network.STA_IF)
        mac = ',"connections": [["mac", "{!s}"]]'.format(
            ubinascii.hexlify(s.config("mac"), ":").decode())
    else:
        mac = ""
    return DISCOVERY_DEVICE_BASE.format(getDeviceID(),
                                        config.VERSION,
                                        mf,
                                        os.uname().sysname if platform != "linux" else "linux",
                                        config.DEVICE_NAME if config.DEVICE_NAME is not None else getDeviceID(),
                                        mac)
