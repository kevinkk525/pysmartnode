'''
Created on 2018-09-21

@author: Kevin Köck
'''

__version__ = "0.5"
__updated__ = "2018-09-25"

import uasyncio as asyncio
import time
import json

_mqtt = None
_log = None

_awaiting_config = False
_has_failed = False
_has_succeeded = False
_config = None
_pyconfig = None


async def requestConfig(config, mqtt, log):
    global _log
    _log = log
    global _mqtt
    _mqtt = mqtt
    global _pyconfig
    _pyconfig = config
    if _awaiting_config:
        return
    asyncio.get_event_loop().create_task(_receiveConfig(log))
    while True:
        await asyncio.sleep_ms(200)
        if _has_failed:
            return False
        elif _has_succeeded:
            global _config
            tmp = _config
            del _config
            return tmp


async def _awaitConfig(topic, msg, retain):
    _log.info("Building components", local_only=True)
    await _mqtt.unsubscribe("{!s}/login/".format(_mqtt.mqtt_home) + _mqtt.id)
    if type(msg) != dict:
        _log.critical("Received config is no dict")
        msg = None
    if msg is None:
        _log.error("Empty configuration received")
        global _has_failed
        _has_failed = True
        return
    else:
        _log.info("received config: {!s}".format(msg), local_only=True)
        # saving components
        _saveComponentsFile(msg)
        global _config
        _config = json.dumps(msg)
        global _has_succeeded
        _has_succeeded = True
        return


async def _receiveConfig(log):
    global _awaiting_config
    global _has_failed
    _awaiting_config = True
    log.info("Receiving config", local_only=True)
    for i in range(1, 4):
        await _mqtt.subscribe("{!s}/login/{!s}".format(_mqtt.mqtt_home, _mqtt.id), _awaitConfig, qos=1,
                              check_retained=False)
        log.debug("waiting for config", local_only=True)
        await _mqtt.publish("{!s}/login/{!s}/set".format(_mqtt.mqtt_home, _mqtt.id), _pyconfig.VERSION, qos=1)
        t = time.ticks_ms()
        while (time.ticks_ms() - t) < 10000:
            if not _has_succeeded:
                await asyncio.sleep_ms(200)
            else:
                _awaiting_config = False
                return
        await _mqtt.unsubscribe("{!s}/login/{!s}".format(_mqtt.mqtt_home, _mqtt.id))
        # unsubscribing before resubscribing as otherwise it would result in multiple callbacks
        # because mqttHandler and subscriptionHandler do not check if function already subscribed.
    _has_failed = True
    _awaiting_config = False
    return


def _saveComponentsFile(msg):
    from pysmartnode.utils import sys_vars
    from sys import platform
    import os
    import gc
    if not sys_vars.hasFilesystem():
        _log.debug("Not saving components as filesystem is unavailable", local_only=True)
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
                    _log.error("Can't save component {!s}, {!s}".format(component, e))
        try:
            os.remove("components.json")
        except Exception as e:
            pass
    else:
        tmp = json.dumps(msg)
        f = open("components.json", "w")
        f.write(tmp)
        f.close()
