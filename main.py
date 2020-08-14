# Author: Kevin Köck
# Copyright Kevin Köck 2017-2020 Released under the MIT license
# Created on 2017-07-14

import time

time.sleep_ms(100)  # give it time to boot before processing code, may repeatedly reset otherwise
import gc

gc.collect()
print(gc.mem_free())
from pysmartnode import main
