'''
Created on 02.02.2018

@author: Kevin Köck
'''

__updated__ = "2019-04-27"

import os
import machine
import ubinascii
import network
from sys import platform
from pysmartnode import config

DISCOVERY_DEVICE_BASE = '{{' \
                        '"ids":"{!s}",' \
                        '"sw":"pysmartnode {!s}",' \
                        '"mf":"{!s}",' \
                        '"mdl":"{!s}",' \
                        '"name": "{!s}",' \
                        '"connections": [["mac", "{!s}"]]' \
                        '}}'


def getDeviceType():
    return os.uname().sysname


def getDeviceID():
    return ubinascii.hexlify(machine.unique_id()).decode()


def hasFilesystem():
    return not os.statvfs("")[0] == 0


def getDeviceDiscovery():
    mf = "espressif" if platform in ("esp8266", "esp32", "esp32_LoBo") else "None"
    s = network.WLAN(network.STA_IF)
    mac = ubinascii.hexlify(s.config("mac"), ":").decode()
    return DISCOVERY_DEVICE_BASE.format(getDeviceID(),
                                        config.VERSION,
                                        mf,
                                        os.uname().sysname,
                                        config.DEVICE_NAME if config.DEVICE_NAME is not None else getDeviceID(),
                                        mac)
