'''
Created on 09.03.2018

@author: Kevin Köck
'''
##
# Configuration management file
##

__updated__ = "2018-10-20"

from config import *
from sys import platform

if platform == "linux" and DEVICE_NAME is None:
    raise TypeError("DEVICE_NAME has to be set on unix port")

# General
VERSION = const(530)
print("PySmartNode version {!s} started".format(VERSION))

import gc
import sys

if DEBUG:
    def __printRAM(start, info=""):
        print(info, "Mem free", gc.mem_free(), "diff:", gc.mem_free() - start)
else:
    __printRAM = lambda *_: None

_mem = gc.mem_free()

from pysmartnode.utils import sys_vars

gc.collect()
__printRAM(_mem, "Imported .sys_vars")

import uasyncio as asyncio

LEN_ASYNC_QUEUE = 20 if platform == "esp8266" else 32
LEN_ASYNC_RQUEUE = 16 if platform == "esp8266" else 32
loop = asyncio.get_event_loop(runq_len=LEN_ASYNC_RQUEUE, waitq_len=LEN_ASYNC_QUEUE)

gc.collect()
__printRAM(_mem, "Imported uasyncio")

gc.collect()
__printRAM(_mem, "Imported os")
from pysmartnode import logging

gc.collect()
_log = logging.getLogger("config")

gc.collect()
__printRAM(_mem, "Imported logging")

if MQTT_TYPE == 1:
    from pysmartnode.networking.mqtt_iot import MQTTHandler, \
        Lock  # Lock possibly needed by other modules
else:  # 0 and wrong configuration options
    from pysmartnode.networking.mqtt_direct import MQTTHandler, \
        Lock  # Lock possibly needed by other modules

gc.collect()
__printRAM(_mem, "Imported MQTTHandler")

COMPONENTS = {}  # dictionary of all configured components
_mqtt = MQTTHandler()
gc.collect()
__printRAM(_mem, "Created MQTT")


def registerComponent(name, data):
    _log.debug("RAM before import registerComponents: {!s}".format(gc.mem_free()), local_only=True)
    import pysmartnode.utils.registerComponents
    gc.collect()
    _log.debug("RAM after import registerComponents: {!s}".format(gc.mem_free()), local_only=True)
    res = pysmartnode.utils.registerComponents.registerComponent(name, data, _log)
    _log.debug("RAM before deleting registerComponents: {!s}".format(gc.mem_free()),
               local_only=True)
    del pysmartnode.utils.registerComponents
    del sys.modules["pysmartnode.utils.registerComponents"]
    gc.collect()
    _log.debug("RAM after deleting registerComponents: {!s}".format(gc.mem_free()),
               local_only=True)
    return res


async def _loadComponentsFile():
    try:
        import components
    except ImportError:
        _log.critical("components.py does not exist")
        return False
    except Exception as e:
        _log.critical("components.py: {!s}".format(e))
        return False
    if hasattr(components, "COMPONENTS") is False:
        return True  # should be all done
    else:
        gc.collect()
        _log.debug("RAM before import registerComponents: {!s}".format(gc.mem_free()),
                   local_only=True)
        import pysmartnode.utils.registerComponents
        gc.collect()
        _log.debug("RAM after import registerComponents: {!s}".format(gc.mem_free()),
                   local_only=True)
        await pysmartnode.utils.registerComponents.registerComponentsAsync(components.COMPONENTS,
                                                                           _log)
        _log.debug("RAM before deleting registerComponents: {!s}".format(gc.mem_free()),
                   local_only=True)
        del pysmartnode.utils.registerComponents
        del sys.modules["pysmartnode.utils.registerComponents"]
        gc.collect()
        _log.debug("RAM after deleting registerComponents: {!s}".format(gc.mem_free()),
                   local_only=True)
        return True


def getComponent(name):
    if name in COMPONENTS:
        return COMPONENTS[name]
    else:
        return None


def getComponentName(component):
    for comp in COMPONENTS:
        if COMPONENTS[comp] == component:
            return comp
    return None


def addComponent(name, obj):
    """
    Add a named component to the list of accessible components.
    These are used to register components using remote configuration or local configuration files.
    """
    if name in COMPONENTS:
        raise ValueError("Component {!s} already registered, can't add".format(name))
    COMPONENTS[name] = obj


def getMQTT():
    return _mqtt


from pysmartnode.utils.component import Component

__printRAM(_mem, "Imported Component base class")

from pysmartnode.components.machine.stats import STATS

__printRAM(_mem, "Imported .machine.stats")
COMPONENTS["STATS"] = STATS()
__printRAM(_mem, "Created .machine.stats.STATS")
