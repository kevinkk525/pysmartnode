# Author: Kevin Köck
# Copyright Kevin Köck 2019 Released under the MIT license
# Created on 2019-04-08 

__updated__ = "2019-04-08"
__version__ = "0.0"

"""
Arduino Instance
{
    package: .arduinoGPIO.arduino
    component: Arduino
    constructor_args: {
        arduinoControl: "ardControlName"   # ArduinoControl instance
        rom: "ArduinoROM"                  # Arduino device ROM 
    }
}

Arduino Pin instance (could also use ArduinoControl Pin)
{
    package: .arduinoGPIO.arduino
    component: Pin
    constructor_args: {
        arduino: "arduinoName"   # Arduino instance
        pin: 4                   # Pin number
        mode: 1                  # Arduino pin mode, ArduinoInteger
        value: 0                 # Starting value of the pin 
    }
}

Arduino ADC instance (could also use ArduinoControl ADC)
{
    package: .arduinoGPIO.arduino
    component: ADC
    constructor_args: {
        arduino: "arduinoName"   # Arduino instance
        pin: 0                   # Pin number
        # vcc: 5                 # Arduino VCC voltage 
    }
}
"""

from pysmartnode.libraries.arduinoGPIO.arduinoGPIO.arduino import Arduino, Pin, ADC
