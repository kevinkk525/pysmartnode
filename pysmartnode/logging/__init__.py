from sys import platform
from pysmartnode import config
import gc

if hasattr(config, "LIGTWEIGHT_LOG") and config.LIGTWEIGHT_LOG is True or \
        platform == "esp8266" and hasattr(config, "LIGTWEIGHT_LOG") is False:
    from pysmartnode.logging.logging_light import getLogger
else:
    from pysmartnode.logging.logging_full import getLogger

gc.collect()
