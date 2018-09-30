'''
Created on 02.02.2018

@author: Kevin Köck
'''

__updated__ = "2018-09-30"

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
