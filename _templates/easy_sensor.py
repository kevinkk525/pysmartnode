'''
Created on 02.06.2018

@author: Kevin Köck
'''

"""
example config (.hjson format, convert if needed differently e.g. as a local .json config):

{
    package: <path_to_your_module>
    component: mySensor
    constructor_args: {
        mqtt_topic: sometopic     #optional, defaults to home/<controller-id>/<sensor_component>
        interval: 600             #optional, defaults to 600
        precision_temp: 2         #optional, precision of the temperature value published
        precision_humid: 1        #optional, precision of the humid value published
        temp_offset: 0            #optional, offset for temperature to compensate bad sensor reading offsets
        humid_offset: 0           #optional, ...
    }
}
"""

__updated__ = "2018-06-02"
__version__ = "0.3"

"""
Works but needs 1.5kB more RAM than the sensor_template
"""

from pysmartnode import config
from pysmartnode import logging
from pysmartnode.utils.wrappers import genericSensor
import gc

####################
# import your library here
from htu21d import HTU21D as Sensor

# choose a component name that will be used for logging (not in leightweight_log) and
# a default mqtt topic that can be changed by received or local component configuration
component_name = "HTU"
####################

log = logging.getLogger(component_name)
mqtt = config.getMQTT()
gc.collect()


class mySensor(genericSensor.SensorWrapper):
    def __init__(self, i2c, precision_temp, precision_humid,  # extend or shrink according to your sensor
                 offset_temp, offset_humid,  # also here
                 interval=None, mqtt_topic=None):
        super().__init__(log, component_name, interval, mqtt_topic, retain=None, qos=None)
        ##############################
        # create sensor object
        self.sensor = Sensor(i2c=i2c)  # add neccessary constructor arguments here
        ##############################

        ##############################
        # adapt to your sensor
        self.temperature = self._registerMeasurement(self.sensor.temperature, precision_temp, offset_temp)
        self.humidity = self._registerMeasurement(self.sensor.humidity, precision_humid, offset_humid)
        ##############################
        # multiple values in one request/publish can be done this way (or manually defined below):
        self.tempHumid = self._registerMultipleMeasurements("temperature", self.temperature, precision_temp,
                                                            "humidity", self.humidity, precision_humid)
        ##############################
        gc.collect()

        ##############################
        # choose a background loop that periodically reads the values and publishes it
        # (function can be created below)
        self._startBackgroundLoop(self.tempHumid)
        ##############################

    ##############################
    # remove or add functions below depending on the combination of values of your sensor
    # if you do not use self._registerMultipleMeasurements
    async def tempHumid(self, publish=True):
        temp = await self.temperature(publish=False)
        humid = await self.humidity(publish=False)
        if temp is not None and humid is not None and publish:
            await mqtt.publish(self.topic, {
                "temperature": ("{0:." + str(self._prec_temp) + "f}").format(temp),
                "humidity": ("{0:." + str(self._prec_humid) + "f}").format(humid)})
            # formating prevents values like 51.500000000001 on esp32_lobo
        return {"temperature": temp, "humiditiy": humid}
    ##############################
