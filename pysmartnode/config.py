'''
Created on 09.03.2018

@author: Kevin Köck
'''
##
# Configuration management file
##

__updated__ = "2018-09-18"

from config import *
from sys import platform

if platform == "linux" and DEVICE_NAME is None:
    raise TypeError("DEVICE_NAME has to be set on unix port")

# General
VERSION = const(500)
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

LEN_ASYNC_QUEUE = 16 if platform == "esp8266" else 32
loop = asyncio.get_event_loop(runq_len=LEN_ASYNC_QUEUE, waitq_len=LEN_ASYNC_QUEUE)

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
    from pysmartnode.networking.mqtt_iot import MQTTHandler, Lock
else:  # 0 and wrong configuration options
    from pysmartnode.networking.mqtt_direct import MQTTHandler, Lock  # Lock possibly needed by other modules

gc.collect()
__printRAM(_mem, "Imported MQTTHandler")

COMPONENTS = {}  # dictionary of all configured components
COMPONENTS["mqtt"] = MQTTHandler(MQTT_RECEIVE_CONFIG)
_components = None  # pointer list of all registered components, used for mqtt
gc.collect()
__printRAM(_mem, "Created MQTT")


async def _registerComponentsAsync(data):
    _log.debug("RAM before import registerComponents: {!s}".format(gc.mem_free()), local_only=True)
    import pysmartnode.utils.registerComponents
    gc.collect()
    _log.debug("RAM after import registerComponents: {!s}".format(gc.mem_free()), local_only=True)
    await pysmartnode.utils.registerComponents.registerComponentsAsync(data, _log)
    _log.debug("RAM before deleting registerComponents: {!s}".format(gc.mem_free()), local_only=True)
    del pysmartnode.utils.registerComponents
    del sys.modules["pysmartnode.utils.registerComponents"]
    gc.collect()
    _log.debug("RAM after deleting registerComponents: {!s}".format(gc.mem_free()), local_only=True)


async def _loadComponentsFile():
    _log.debug("RAM before import loadComponentsFile: {!s}".format(gc.mem_free()), local_only=True)
    import pysmartnode.utils.loadComponentsFile
    gc.collect()
    _log.debug("RAM after import loadComponentsFile: {!s}".format(gc.mem_free()), local_only=True)
    data = await pysmartnode.utils.loadComponentsFile.loadComponentsFile(_log, _registerComponentsAsync)
    _log.debug("RAM before deleting loadComponentsFile: {!s}".format(gc.mem_free()), local_only=True)
    del pysmartnode.utils.loadComponentsFile
    del sys.modules["pysmartnode.utils.loadComponentsFile"]
    gc.collect()
    _log.debug("RAM after deleting loadComponentsFile: {!s}".format(gc.mem_free()), local_only=True)
    if type(data) == dict:
        _log.debug("RAM before import registerComponents: {!s}".format(gc.mem_free()), local_only=True)
        import pysmartnode.utils.registerComponents
        gc.collect()
        _log.debug("RAM after import registerComponents: {!s}".format(gc.mem_free()), local_only=True)
        await pysmartnode.utils.registerComponents.registerComponentsAsync(data, _log)
        _log.debug("RAM before deleting registerComponents: {!s}".format(gc.mem_free()), local_only=True)
        del pysmartnode.utils.registerComponents
        del sys.modules["pysmartnode.utils.registerComponents"]
        gc.collect()
        _log.debug("RAM after deleting registerComponents: {!s}".format(gc.mem_free()), local_only=True)
        return True
    return data  # data is either True or False


def getComponent(name):
    if name in COMPONENTS:
        return COMPONENTS[name]
    else:
        return None


def addNamedComponent(name, obj):
    """
    Add a named component to the list of accessible components.
    These are used to register components using remote configuration or local configuration files.
    """
    if name in COMPONENTS:
        raise ValueError("Component {!s} already registered, can't add".format(name))
    COMPONENTS[name] = obj


def getMQTT():
    if "mqtt" in COMPONENTS:
        return COMPONENTS["mqtt"]
    return None


def addComponent(obj):
    """Add a component to the list of all used components. Used for mqtt"""
    global _components
    if _components is None:
        _components = obj
    else:
        c = _components
        while c is not None:
            if c._next_component is None:
                c._next_component = obj
                return
            c = c._next_component


from pysmartnode.components.machine.stats import STATS

__printRAM(_mem, "Imported .machine.stats")
COMPONENTS["STATS"] = STATS()
__printRAM(_mem, "Created .machine.stats.STATS")
