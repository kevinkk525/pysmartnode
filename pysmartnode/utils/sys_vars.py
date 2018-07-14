'''
Created on 02.02.2018

@author: Kevin Köck
'''

__updated__ = "2018-07-13"

import os
import machine
import ubinascii
import sys


def getDeviceType():
    return os.uname().sysname


def getDeviceID():
    return ubinascii.hexlify(machine.unique_id()).decode()


def hasFilesystem():
    return not os.statvfs("")[0] == 0


def unloadModule(mod):
    # removes module from the system, but in my test did not free all RAM used by module
    mod_name = mod.__name__
    if mod_name in sys.modules:
        del sys.modules[mod_name]
