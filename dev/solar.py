'''
Created on 2018-07-18

@author: Kevin Köck
'''

"""
example config:
{
    package: .machine.solar
    component: Solar
    constructor_args: {
        pin: 2 # pin number where the relais for the solar charger is connected (HIGH for connected)
        adc: 4 # optional, adc pin of the connected light resistor
        light_charging: 50 # light percentage above which charging will be started
        light_disconnecting: 30 # light percentage below which charging will be stopped
        voltage_max_light: 0.5
        voltage_min_light: 3.0 
        battery_voltage_stop: 12
        # precision_light: 2 # optional, the precision of the light value published by mqtt
        # interval_light: 600     # optional, defaults to 600s, interval in which light value gets published
        # mqtt_topic: null  # optional, defaults to <home>/<device-id>/solar/charging [ON/OFF]
        # mqtt_topic_light: null  # optional, defaults to <home>/<device-id>/solar/light [percentage]
        # interval_watching: 1 # optional, the interval in which the voltage and light will be checked, defaults to 1s     
    }
}
"""

__version__ = "0.1"
__updated__ = "2018-07-16"
