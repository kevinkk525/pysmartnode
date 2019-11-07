# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-10-30 

__updated__ = "2019-10-30"
__version__ = "0.1"

# Generate component definitions from Homeassistant website by replacing the documentation list


list_binary = ''' battery: On means low, Off means normal
cold: On means cold, Off means normal
connectivity: On means connected, Off means disconnected
door: On means open, Off means closed
garage_door: On means open, Off means closed
gas: On means gas detected, Off means no gas (clear)
heat: On means hot, Off means normal
light: On means light detected, Off means no light
lock: On means open (unlocked), Off means closed (locked)
moisture: On means moisture detected (wet), Off means no moisture (dry)
motion: On means motion detected, Off means no motion (clear)
moving: On means moving, Off means not moving (stopped)
occupancy: On means occupied, Off means not occupied (clear)
opening: On means open, Off means closed
plug: On means device is plugged in, Off means device is unplugged
power: On means power detected, Off means no power
presence: On means home, Off means away
problem: On means problem detected, Off means no problem (OK)
safety: On means unsafe, Off means safe
smoke: On means smoke detected, Off means no smoke (clear)
sound: On means sound detected, Off means no sound (clear)
vibration: On means vibration detected, Off means no vibration (clear)
window: On means open, Off means closed'''

list_sensor = '''battery: Percentage of battery that is left.
humidity: Percentage of humidity in the air.
illuminance: The current light level in lx or lm.
signal_strength: Signal strength in dB or dBm.
temperature: Temperature in °C or °F.
power: Power in W or kW.
pressure: Pressure in hPa or mbar.
timestamp: Datetime object or timestamp string.'''


def generateList(b, binary: bool):
    b = b.split("\n")
    for i, v in enumerate(b):
        b[i] = v[:v.find(":")]
    for i in b:
        print("SENSOR_{!s}{!s} = {!r}".format("BINARY_" if binary else "", i.upper(), i))


print("# Sensors")
generateList(list_sensor, False)
print("\n# Binary sensors")
generateList(list_binary, True)
