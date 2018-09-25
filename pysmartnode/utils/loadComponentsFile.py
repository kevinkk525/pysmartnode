'''
Created on 2018-09-25

@author: Kevin Köck
'''

__version__ = "0.1"
__updated__ = "2018-09-25"

from pysmartnode.utils import sys_vars
import json
from sys import platform
import gc
import uasyncio as asyncio
import os


def _importComponents(_log):
    try:
        import components
    except ImportError:
        _log.critical("components.py does not exist")
        return False
    except Exception as e:
        _log.ciritcal("components.py: {!s}".format(e))
        return False
    if hasattr(components, "COMPONENTS"):
        _log.info("Trying to register COMPONENTS of components.py", local_only=True)
        return components.COMPONENTS
    else:
        _log.info("No COMPONENTS in components.py, maybe user code executed", local_only=True)
        return True


async def loadComponentsFile(_log, registerComponentsAsync):
    if not sys_vars.hasFilesystem():
        comps = _importComponents(_log)
        if comps is False:
            _log.critical("Can't load components file as filesystem is unavailable")
            return False
        return comps
    try:
        f = open("components.json", "r")
        components_found = True
    except OSError:
        components_found = False
    if components_found is False:
        try:
            f = open("_order.json", "r")
        except Exception as e:
            # if loading configuration jsons fails, try to import components.py
            comps = _importComponents(_log)
            if comps is False:
                _log.critical("_order.json does not exist, {!s}".format(e))
                return False
            else:
                return comps
        order = json.loads(f.read())
        f.close()
        gc.collect()
        for component in order:
            tmp = {"_order": [component]}
            try:
                f = open("components/{!s}.json".format(component), "r")
                tmp[component] = json.loads(f.read())
                f.close()
                await registerComponentsAsync(tmp)
            except Exception as e:
                _log.error("Error loading component file {!s}, {!s}".format(component, e))
            gc.collect()
            if platform == "esp8266":
                await asyncio.sleep(1)
                # gives time to get retained topic and settle ram, important on esp8266
            else:
                await asyncio.sleep_ms(100)
            gc.collect()
        return True
    else:
        c = f.read()
        f.close()
        try:
            c = json.loads(c)
            gc.collect()
            return c
        except Exception as e:
            _log.critical("components.json parsing error {!s}".format(e))
            return False
