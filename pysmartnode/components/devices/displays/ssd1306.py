'''
Created on 28.10.2017

@author: Kevin Köck
'''

"""
example config:

{
    package: .devices.displays.ssd1306
    component: SSD1306_easy     #or SSD1306_complex
    constructor_args: {
        i2c: "i2c"   #i2c object registered earlier
        width: null        #optional, defaults to 128
        height: null       #optional, defaults to 32
        mqtt_topic: null  #optional, defaults to home/<controller-id>/ssd1306/set
    }
}
"""

__updated__ = "2018-05-20"
__version__ = "0.3"

import gc
from pysmartnode import logging

try:
    import ssd1306
except:
    from pysmartnode.libraries import ssd1306
from pysmartnode import config

_mqtt = config.getMQTT()

_log = logging.getLogger("SSD1306")
gc.collect()


# load class package dynamically by config and execute functions from mqtt
# message by hasattr(...)
class SSD1306_easy(ssd1306.SSD1306_I2C):
    def __init__(self, i2c, width=128, height=32, mqtt_topic=None):
        super().__init__(width, height, i2c)
        mqtt_topic = mqtt_topic or _mqtt.getDeviceTopic("ssd1306", is_request=True)
        _mqtt.scheduleSubscribe(mqtt_topic, self.write)
        self.fill(0)
        self.show()

    async def write(self, topic, msg, retain):
        try:
            text = msg["message"]["text"]
            x = msg["message"]["x"]
            y = msg["message"]["y"]
            if "color" in msg["message"]:
                color = msg["message"], ["color"]
            else:
                color = 1
        except Exception as e:
            _log.error("error in function write in SSD1306_easy: {!s}".format(e))
            return False
        self.fill(0)  # not good because not posible to add another text additionally
        self.text(text, x, y, color)
        self.show()
        return True


class SSD1306_complex(SSD1306_easy):
    def __init__(self, i2c, width=128, height=32, mqtt_topic=None):
        super().__init__(i2c, width, height, mqtt_topic)
        try:
            import gfx
            self.gfx = gfx.GFX(width, height, self.pixel,
                               hline=self._fast_hline, vline=self._fast_vline)
        except Exception as e:
            _log.critical(
                "Could not import gfx module, SSD1306_complex not possible, error {!s}".format(e))

    def _fast_hline(self, x, y, width, color):
        self.fill_rect(x, y, width, 1, color)

    def _fast_vline(self, x, y, height, color):
        self.fill_rect(x, y, 1, height, color)

    async def write(self, topic, msg, retain):
        # tbd
        print(msg)
        if msg["message"]["type"] == "text":
            return await super().write(msg)
        # for obj in data["message"]:
        #    self.write/....
