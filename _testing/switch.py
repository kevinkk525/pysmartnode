# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-09-09 

__updated__ = "2019-09-09"
__version__ = "0.0"

from pysmartnode.utils.component.switch import ComponentSwitch as _Switch
from pysmartnode import config
from pysmartnode import logging

mqtt = config.getMQTT()
log = logging.getLogger("Switch")


class Switch(_Switch):
    def __init__(self):
        super().__init__("testswitch", mqtt.getDeviceTopic("switch", is_request=True), "switch")
        self._frn = "Testswitch"
        log.info("State: {!s}".format(self._state), local_only=True)

    async def _on(self):
        log.info("State: {!s}".format(True if self._state is False else False), local_only=True)
        return True

    async def _off(self):
        log.info("State: {!s}".format(False if self._state is True else True), local_only=True)
        return True
