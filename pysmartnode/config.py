# Author: Kevin Köck
# Copyright Kevin Köck 2018-2019 Released under the MIT license
# Created on 2018-03-09

##
# Configuration management file
##

__updated__ = "2018-11-04"

from .config_base import *
from sys import platform

if platform == "linux" and DEVICE_NAME is None:
    raise TypeError("DEVICE_NAME has to be set on unix port")

# General
VERSION = const(601)
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

from pysmartnode.networking.mqtt import MQTTHandler, Lock  # Lock possibly needed by other modules

gc.collect()
__printRAM(_mem, "Imported MQTTHandler")

COMPONENTS = {}  # dictionary of all configured components
_mqtt = MQTTHandler()
gc.collect()
__printRAM(_mem, "Created MQTT")


async def registerComponent(name, data=None):
    """
    Can be used to register a component with name and data dict.
    Also possible to register multiple components when passing dictionary as name arg
    :param name: str if data is dict, else dict containing multiple components
    :param data: dict if name given, else None
    :return: bool
    """
    _log.debug("RAM before import registerComponents:", gc.mem_free(), local_only=True)
    import pysmartnode.utils.registerComponents
    gc.collect()
    _log.debug("RAM after import registerComponents:", gc.mem_free(), local_only=True)
    if data is None:
        res = await pysmartnode.utils.registerComponents.registerComponentsAsync(name, _log)
    else:
        res = pysmartnode.utils.registerComponents.registerComponent(name, data, _log)
    _log.debug("RAM before deleting registerComponents:", gc.mem_free(), local_only=True)
    del pysmartnode.utils.registerComponents
    del sys.modules["pysmartnode.utils.registerComponents"]
    gc.collect()
    _log.debug("RAM after deleting registerComponents:", gc.mem_free(), local_only=True)
    return res


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
