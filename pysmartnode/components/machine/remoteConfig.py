# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-15 

__updated__ = "2019-10-20"
__version__ = "0.5"

from pysmartnode.utils.component import Component
from pysmartnode import config
from pysmartnode import logging
import uasyncio as asyncio
from sys import platform
import gc

COMPONENT_NAME = "remoteConfig"

_mqtt = config.getMQTT()
_log = logging.getLogger(COMPONENT_NAME)

WAIT = 1.5 if platform == "esp8266" else 0.5


class RemoteConfig(Component):
    def __init__(self):
        super().__init__(COMPONENT_NAME, __version__)
        self._topic = "{!s}/login/{!s}/#".format(_mqtt.mqtt_home, _mqtt.client_id)
        self._watcher_coro = self._watcher()
        self._icomp = None
        self._rcomp = []
        self._done = False
        asyncio.get_event_loop().create_task(self._watcher_coro)

    def done(self):
        return self._done

    async def _watcher(self):
        mqtt = _mqtt
        mqtt.subscribe(self._topic, self.on_message, self)
        try:
            while True:
                while mqtt.isconnected() is False:
                    await asyncio.sleep(1)
                if await mqtt.awaitSubscriptionsDone(await_connection=False):
                    _log.debug("waiting for config", local_only=True)
                    await _mqtt.publish(
                        "{!s}/login/{!s}/set".format(mqtt.mqtt_home, mqtt.client_id),
                        [config.VERSION, platform, WAIT])
                    gc.collect()
                else:
                    await asyncio.sleep(20)
                    continue
                for _ in range(120):
                    if mqtt.isconnected() is False:
                        break
                    await asyncio.sleep(1)
                    # so that it can be cancelled properly every second
        except asyncio.CancelledError:
            if config.DEBUG is True:
                _log.debug("_watcher cancelled", local_only=True)
        except Exception as e:
            await _log.asyncLog("error", "Error watching remoteConfig: {!s}".format(e))
        finally:
            await mqtt.unsubscribe(self._topic, self)
            self._done = True

    def _saveComponent(self, name, data):
        pass
        # save if save is enabled

    async def on_message(self, topic, msg, retain):
        if retain is True:
            return False
        m = memoryview(topic)
        if m[-4:] == b"/set":
            return False
        if m == memoryview(self._topic)[:-2]:
            print("received amount", msg)
            self._icomp = int(msg)
            # no return so it can end if 0 components are expected
        elif self._icomp is None:
            await _log.asyncLog("error", "Need amount of components first")
            return False
        else:
            if type(msg) != dict:
                await _log.asyncLog("error", "Received config is no dict")
                return False
            name = topic[topic.rfind("/") + 1:]
            del topic
            gc.collect()
            _log.info("received config for component {!s}: {!s}".format(name, msg),
                      local_only=True)
            if name in self._rcomp:
                # received config already, typically happens if process was
                # interrupted by network error
                return False
            self._rcomp.append(name)
            self._saveComponent(name, msg)
            config.registerComponent(name, msg)
        if len(self._rcomp) == self._icomp:  # received all components
            asyncio.cancel(self._watcher_coro)
        return False
