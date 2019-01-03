'''
Created on 14.07.2017

@author: Kevin Köck
'''

import time

time.sleep_ms(250)  # give it time to boot before processing code, may repeatedly reset otherwise
import gc

gc.collect()
print(gc.mem_free())
from pysmartnode import main
