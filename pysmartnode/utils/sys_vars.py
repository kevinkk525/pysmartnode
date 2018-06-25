'''
Created on 02.02.2018

@author: Kevin K?ck
'''

__updated__ = "2018-05-20"

import os
import machine
import ubinascii


def getDeviceType():
    return os.uname().sysname


def getDeviceID():
    return ubinascii.hexlify(machine.unique_id()).decode()


def hasFilesystem():
    return not os.statvfs("")[0] == 0
