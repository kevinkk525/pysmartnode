'''
Created on 09.03.2018

@author: Kevin Köck
'''
##
# Config file
##

__updated__ = "2018-05-26"

from config import *

# General
VERSION = 381
print("PySmartNode version {!s} started".format(VERSION))

import gc
import json
import os
import time

if DEBUG:
    def __printRAM(start, info=""):
        print(info, "Mem free", gc.mem_free(), "diff:", gc.mem_free() - start)
else:
    __printRAM = lambda *_: None

_mem = gc.mem_free()

from pysmartnode.utils import sys_vars

id = sys_vars.getDeviceID()
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
log = logging.getLogger("config")
log.setLoop(loop)

gc.collect()
__printRAM(_mem, "Imported logging")

from pysmartnode.networking.mqtt import MQTTHandler, Lock  # Lock possibly needed by other code

gc.collect()
__printRAM(_mem, "Imported MQTTHandler")

COMPONENTS = {}
COMPONENTS["mqtt"] = MQTTHandler(MQTT_RECEIVE_CONFIG, True)
log.setMQTT(COMPONENTS["mqtt"])
gc.collect()
__printRAM(_mem, "Created MQTT")

from sys import platform

if platform == "esp8266":
    pins = {"D0": 16, "D1": 5, "D2": 4, "D3": 0, "D4": 2,
            "D5": 14, "D6": 12, "D7": 13, "D8": 15, "D9": 3, "D10": 1}
else:
    pins = {}


def _checkArgs(d):
    required = ["package", "component"]
    optional = {
        "constructor_args": None,
        "init_function": None,
        "init_args": None,
        "call_function_regularly": None,
        "call_interval": None
    }
    for r in required:
        if r not in d:
            log.error("Missing required value {!r} in component".format(r))
            return False
    for o in optional:
        if o not in d:
            d[o] = optional[o]
    return True


def _getKwargs(kwargs):
    if type(kwargs) != dict:
        return {}
    for key in kwargs:
        arg = kwargs[key]
        if type(arg) == str:
            if arg in COMPONENTS:
                kwargs[key] = COMPONENTS[arg]
    return kwargs


def _getArgs(args):
    if type(args) != list:
        return []
    for i in range(0, len(args)):
        if type(args[i]) == str:
            if args[i] in COMPONENTS:
                args[i] = COMPONENTS[args[i]]
    return args


def _checkPackage(data):
    if data["package"][:1] == ".":
        data["package"] = "pysmartnode.components" + data["package"]


queue_overflow = False


async def registerComponentsAsync(data):
    global queue_overflow
    for component in data["_order"]:
        tmp = {"_order": [component]}
        tmp[component] = data[component]
        registerComponents(tmp)
        del tmp
        gc.collect()
        await asyncio.sleep_ms(750 if platform == "esp8266" else 200)
        st = time.ticks_ms()
        while len(loop.runq) > LEN_ASYNC_QUEUE - 6 and time.ticks_ms() - st < 8000:
            if platform == "esp8266":
                await asyncio.sleep_ms(500)
                # gives time to get retained topic and settle ram, important on esp8266
            else:
                await asyncio.sleep_ms(200)
        if time.ticks_ms() - st > 8000 and len(loop.runq) > LEN_ASYNC_QUEUE - 6:
            log.critical("Runq > {!s} ({!s}) for more than 8s".format(LEN_ASYNC_QUEUE - 6, len(loop.runq)),
                         local_only=queue_overflow)
            if queue_overflow is False:
                queue_overflow = True  # to prevent multiple loggings only log locally after first log
        gc.collect()


def registerComponents(data):
    gc.collect()
    mem_start = gc.mem_free()
    __printRAM(mem_start)
    if "_order" not in data:
        log.critical("missing order list _order, can't add components")
        return False
    res = False
    # res: Result of registering a component
    # makes only sense if only a single component is being registered at a time
    order = data["_order"] if "_order" in data else list(data.keys())
    for i in range(0, len(order)):
        if order[i] not in data:
            log.critical("component {!r} of order is not in component dict".format(data["_order"][i]))
        else:
            version = None
            componentname = order[i]
            if componentname in COMPONENTS:
                log.critical("Component {!r} already added".format(componentname))
            else:
                component = data[componentname]
                if _checkArgs(data[componentname]):
                    _checkPackage(data[componentname])
                    try:
                        tmp = __import__(component["package"], globals(),
                                         locals(), [component["component"]], 0)
                    except Exception as e:
                        log.critical("Error importing package {!s}, error: {!s}".format(
                            component["package"], e))
                        tmp = None
                    gc.collect()
                    err = False
                    if tmp is not None:
                        if hasattr(tmp, "__version__"):
                            version = getattr(tmp, "__version__")
                        if hasattr(tmp, component["component"]):
                            kwargs = _getKwargs(component["constructor_args"]) if type(
                                component["constructor_args"]) == dict else {}
                            args = _getArgs(component["constructor_args"]) if type(
                                component["constructor_args"]) == list else []
                            try:
                                obj = getattr(tmp, component["component"])(*args, **kwargs)
                            except Exception as e:
                                log.error(
                                    "Error during creation of object {!r}, {!r}, version {!s}, error: {!s}".format(
                                        component["component"], componentname, version, e))
                                obj = None
                                err = True
                            if obj is not None:
                                err = False
                                if component["init_function"] is not None:
                                    kwargs = _getKwargs(component["init_args"]) if type(
                                        component["init_args"]) == dict else {}
                                    args = _getArgs(component["init_args"]) if type(
                                        component["init_args"]) == list else []
                                    if hasattr(obj, component["init_function"]):
                                        init = getattr(obj, component["init_function"])
                                        if type(init) == type(registerComponentsAsync):
                                            from pysmartnode.utils.wrappers.callAsyncSafe import \
                                                callAsyncSafe as _callAsyncSafe
                                            loop.create_task(_callAsyncSafe(
                                                init, component["init_function"], args, kwargs))
                                        else:
                                            try:
                                                tmp_init = init(*args, **kwargs)
                                                if type(tmp_init) == type(registerComponentsAsync):
                                                    loop.create_task(tmp_init)
                                            except Exception as e:
                                                log.critical(
                                                    "Error calling init function {!r}, {!r}, version {!s}, error: {!e}".format(
                                                        component["init_function"], componentname, version, e))
                                                err = True
                                    else:
                                        log.critical(
                                            "init function {!r} does not exist for object {!r}, version {!s}".format(
                                                component["init_function"], componentname, version))
                                        err = True
                                if err is False and component["call_function_regularly"] is not None:
                                    if hasattr(obj, component["call_function_regularly"]) is False:
                                        log.critical("obj has no function {!r}".format(
                                            component["call_function_regularly"]))
                                    else:
                                        func = getattr(obj, component["call_function_regularly"])
                                        from pysmartnode.utils.wrappers.callRegular import callRegular
                                        loop.create_task(callRegular(func, component["call_interval"]))
                                if err is False:
                                    COMPONENTS[componentname] = obj
                                    log.info("Added component {!r}, version {!s}".format(
                                        componentname, version))
                                    res = True
                            elif err is False:
                                log.info("Added component {!r} as service, version {!s}".format(
                                    componentname, version))  # probably function, not class
                                res = True
                            else:
                                res = False
                        else:
                            log.critical("error during import as object does not exist in module {!s}".format(
                                component["component"]))
                            res = False
            gc.collect()
            __printRAM(mem_start)
    return res


def _importComponents():
    try:
        import components
    except ImportError:
        log.critical("components.py does not exist")
        return False
    except Exception as e:
        log.ciritcal("components.py: {!s}".format(e))
        return False
    if hasattr(components, "COMPONENTS"):
        log.info("Trying to register COMPONENTS of components.py")
        return registerComponents(components.COMPONENTS)
    else:
        log.info("No COMPONENTS in components.py, maybe user code executed")
        return True


async def loadComponentsFile():
    if not sys_vars.hasFilesystem():
        if not _importComponents():
            log.critical("Can't load components file as filesystem is unavailable")
            return False
        return True
    try:
        f = open("components.json", "r")
        components_found = True
    except OSError:
        components_found = False
    if components_found is False:
        try:
            f = open("_order.json", "r")
        except Exception as e:
            if not _importComponents():
                log.critical("_order.json does not exist, {!s}".format(e))
                return False
            else:
                return True
        order = json.loads(f.read())
        f.close()
        gc.collect()
        for component in order:
            tmp = {"_order": [component]}
            try:
                f = open("components/{!s}.json".format(component), "r")
                tmp[component] = json.loads(f.read())
                f.close()
                registerComponents(tmp)
                del tmp
            except Exception as e:
                log.error("Error loading component file {!s}, {!s}".format(component, e))
            gc.collect()
            if platform == "esp8266":
                await asyncio.sleep(1)
                # gives time to get retained topic and settle ram, important on esp8266
            else:
                await asyncio.sleep_ms(100)
            gc.collect()
    else:
        c = f.read()
        f.close()
        try:
            c = json.loads(c)
            gc.collect()
            registerComponents(c)
            return True
        except Exception as e:
            log.critical("components.json parsing error {!s}".format(e))
            return False


def saveComponentsFile(msg):
    if not sys_vars.hasFilesystem():
        log.debug("Not saving components as filesystem is unavailable", local_only=True)
        return
    if platform == "esp8266":
        tmp = json.dumps(msg["_order"])
        f = open("_order.json", "w")
        f.write(tmp)
        f.close()
        del tmp
        try:
            os.mkdir("components")
        except Exception as e:
            # probably already there
            f = os.listdir("components")
            for file in f:
                os.remove("components/" + file)
            del f
            gc.collect()
        for component in msg:
            if component != "_order":
                try:
                    f = open("components/{!s}.json".format(component), "w")
                    f.write(json.dumps(msg[component]))
                    f.close()
                except Exception as e:
                    log.error("Can't save component {!s}, {!s}".format(component, e))
        try:
            os.remove("components.json")
        except Exception as e:
            pass
    else:
        tmp = json.dumps(msg)
        f = open("components.json", "w")
        f.write(tmp)
        f.close()


def getComponent(name):
    if name in COMPONENTS:
        return COMPONENTS[name]
    else:
        return None


def addComponent(name, obj):
    if name in COMPONENTS:
        raise ValueError("Component {!s} already registered, can't add".format(name))
    COMPONENTS[name] = obj


def getMQTT():
    return COMPONENTS["mqtt"]
