# Changelog

---------------------------------------------------
### Version 6.0.1
* [MQTT] Fix unsubscribe race condition

---------------------------------------------------
### Version 6.0.0
* [easyGPIO] topics now use "easyGPIO" to not make them not collide with module "switches.GPIO"
* [remoteSensors] use remote sensors as if they were locally connected
* [remoteSwitch] use a remote switch as if it was locally connected
* [COMPONENTS] extended API significantly, updated to new/changed MQTT features, added cleanup method
* [SENSOR COMPONENT] major base class for a unified sensor API and features to make usage and development easier
* [Sensors] updated all sensors to use the new SENSOR COMPONENT. Some sensors therefore experience breaking changes in configuration, default topics and behaviour.
* [DS18] rewritten for new sensor API
* [HEATER] removed deprecated component
* [CLIMATE] added new Climate component which is compatible to homeassistant MQTT Climate
* [CONFIG] removed option to load components from .json files, use components.py instead
* [STATS] Major update, publishing many device stats as hass json_attributes and RSSI as main value instead of "online/offline" which is now done directly in mqtt as availability topic. Published values: (last_boot, uptime, pysmartnode version, micropython firmware version, RAM free, RSSI, MQTT Downtime, MQTT Reconnects, Asyncio waitq used size)
* [MQTT] Improvements, Subscriptions done by mqtt not by components, Subscribing uses subscription chain and can be called non-blocking synchronously, added easy way to restore a device state from a state topic of a subscribed command_topic, prevention of uasyncio queue overflows when receiving too many messages
* [LOGGING] Extended asyncLog() method with kwargs "timeout" and "await_connection" just like mqtt.publish
* [LOGGING] Now works similar to print expecting multiple args instead of one message string. Optimizes RAM usage (especially with local_only logging).
* [TOOLS] updated esp8266 build scripts, script to strip variable type hints as those are not yet supported by micropython
* [CONFIG] config.py update, made configuration easier and smaller by freezing standard values in ROM and custom configs in config.py will just overwrite those.

---------------------------------------------------
### Version 5.2.0
* [WIFI] reworked duplicate wifi code, optimized wifi/mqtt handling
* [WIFI_LED] now also blinks on wifi (dis-)connect and mqtt reconnect
* [MQTT] Introduction of operation timeout and connection checks to prevent code from being blocked by network issues
* [MQTT] important bugfix if receive_config = False
* [MQTT] multiple optimizations, generalizations, code safety improvements
* [MQTT] changed API from async def publish(self, topic, msg, qos=0, retain=False) back to async def publish(self, topic, msg, retain=False, qos=0) to stay compatible to umqtt library although differently from paho-mqtt
* [COMPONENTS] optimized and extended Switch and Button classes

---------------------------------------------------
### Version 5.1.0
* [MQTT] Bugfixes in unsubscribe()
* [WEBREPL] It is now possible to configure the webrepl in config.py and it will automatically be started.
* [COMPONENTS] Extended by a generic SWITCH class. See description, adds "on" and "off" coroutines so it can be controlled by other components
* [Templates] Extended the Switch template with "on" and "off" coroutines
* [Generic_Switch] Wrapper for all SWITCH classes using the Switch template to extend functionality (e.g. safety shutdown, repeating mode, ...)
* [Bell] Bugfix and moved to "sensors" package
* [Switches] New package that better reflects the 2 basic component types sensors and switches
* [LED, Buzzer] moved to package "switches"
* [GPIO] moved to package "switches". easyGPIO however stays in "machine" as it is very generic and can be used as both sensor and switch
* Various beautifications, small bugfixes and optimizations

---------------------------------------------------
### Version 5.0.1
* [MQTT] Port is configureable now
* [ESP8266 WIFI] Possibility to set wifi sleep mode. No sleep makes wifi more reliable
* [UNIX] Module improvements, new module RF-Pump in new custom-component directory outside standard components
* [Tools] Updated scripts to set up initial repositories for building firmware for esp8266/esp32
* [WIFI-LED] Added option to activate a LED in config.py that displays the wifi status (5 short blinks on initial connect, 1 short blink every 30secs when connected, 3 long blinks every 5secs when not connected).
* [GPIO] GPIO module supports setting pins active_low 

---------------------------------------------------
#### Version 5.0.0
* [MQTT] Integrated Homeassistant mqtt discovery feature
* [COMPONENTS] Completely changed the way components are integrated to support homeassistant mqtt discovery. Every component now has to use a common base component class. This is a major change breaking compatibility with previous pysmartnode/components versions and often component configurations. 
* [COMPONENTS, MQTT] Mqtt subscriptions are not callback based anymore but component based. But within a component they are callback based.
* [COMPONENTS] Updated most components accordingly. Some topics and configurations have changed, check your configs! Not updated components were moved to _dev as they need more looking at.
* [Templates] Updated templates.
* [RAM] component is now part of a basic system component.
* [DS18] Component completely rewritten. It is now fully separated into a controller and a unit object. The controller has control over the onewire bus and reads all configured units. (Having other onewire devices on the same bus should be possible. No common onewire controller integrated at the moment). The DS18 unit object supports homeassistant discovery and therefore every DS18 unit connected to the controller has to be configured, unless auto-discovery is enabled on the controller, which will just create an object for each found sensor (this however makes using these in other components impossible and only serves to publish read temperatures).
* [UNIX] Added support for unix port of Micropython! (Most sensors won't be available as it doesn't have a gpio interface, working on an interface for the Pi). But you can execute system commands and e.g. use the rf433 raspberry-remote library
* [STATS] component now also publishes the wifi signal strength.

---------------------------------------------------
#### Version 4.1.1
* [HCSR04] Added module to measure distance
* [WaterSensor] Simple water sensor using 2 wires
* Small fixes in ArduinoControl

---------------------------------------------------
#### Version 4.1.0
* Dropped official support of ESP32_Loboris_Fork because of lack of updates (no commit since 7 months). No code has been removed and modules are even updated to support it so could still mostly work on that fork, I just won't test it on that platform myself.
* Support for mainline ESP32 as all important bugs are finally fixed now
* [ecMeter] added module to measure EC with a simple cable
* [ds18] multiple bugfixes and improvements. Support for instanciating a single DS18 unit
* [ADC] updated to support ESP32 mainline. New interface and subclass logic to support custom ADC classes using external ADCs (like the Arduino)
* [Amux] improvements, supports Arduino ADCs & Pins -> possible to connect an AnalogMultiplexer to an Arduino and control remotely
* [ArduinoControl] Added library to control an Arduino by communication by 1-wire protocol

---------------------------------------------------
#### Version 4.0.7
* [mqtt] changed API from async def publish(self, topic, msg, retain=False, qos=0) to def publish(self, topic, msg, qos=0, retain=False)
* [mqtt] added experimental support for a not yet published proxy for mqtt (micropython_iot_generic + micropyhton_iot)
* [moisture] changed name and small improvements

---------------------------------------------------
#### Version 4.0.6
* [heater] bugfix for unknown hardware initialization status on reboot (resulting in heater being ON although not detected)
* updated README with additional information about esp8266 heap size changes
* [watchdog] use RTC memory as backup on ESP8266 if filesystem is unavailable
* Reliability improvement to main.py
* [heater] Reliability improvement to heater plugin daynight

---------------------------------------------------
#### Version 4.0.5
* minor bugfixes and improvements
* updated README
* updated components.py template

---------------------------------------------------
#### Version 4.0.4
* lots of improvments, RAM optimizations (sadly eaten by improvements)
* [config, mqtt] If no local configuration is available and no configuration is received, it will now ask for configuration periodically, waiting for the broker/SmartServer to get online again (prevents running without any configuration and needing a hard reset to get config again)
* [mqtt] supports now "unsubcribe"
* [mqtt] Usage of subscription module as it now supports wildcards, saves some RAM. Also stores device subscriptions shortened to save some RAM.
* [components] added lots of new components like deepsleep, battery, button, switch, heater
* [PIN, ADC] added unified interface for machine.Pin and machine.ADC accepting pin names for esp8266 nodeMCU and unifying the usage of ADC between esp8266 and esp32_LoBo so you don't have to check each port for its return values etc.
* [developers] for developers of components: pysmartnode.config.pins is now deprecated and removed, usage of unified Pin() object pysmartnode.components.machine.pin.Pin is recommended. See module for explanation

---------------------------------------------------
#### Version 3.8.2
* RAM optimizations (400B freed)

---------------------------------------------------
#### Version 3.8.1
* first version published to github
* smaller bugfixes
* [mqtt] "last_boot" was not published as retained
* [templates] finished template "easy_sensor.py" for creating a new sensor supporting the sensor-API and automatically publishes readings with minimal effort
* [templates] finished template "sensor_template.py" for creating a new sensor with a little more effort but ~1.5kB less RAM
* [templates] finished template "component_template.py" for creating a generic component which is not a sensor
* [uasyncio] loop with 32 slots is used on esp32 as they could get full easily with multiple async sensors and esp32 has enough RAM

---------------------------------------------------
#### Version 3.8.0
* [config] made usage of lightweight logging module configurable, defaults to lightweight for esp8266
* [esp8266] added possibility to use ntptime, also adapted logging_full to support it as strftime is not available on esp8266
* [mqtt] publish time of boot to "./last_boot" if rtc_sync is active
* [config] made usage of minimal MQTTClient configurable (saves ~200B on esp8266 as frozen bytecode)
* [config] providing a component configuration is now possible as component.py; either containing a dictionary "COMPONENTS" (makes component configuration as frozen module possible) or as a starting module for a manual loading of modules
* [wifi] ftp, ntp-sync, etc will now be started as soon as a wifi connection is established if the first try failed
* [watchdog] added watchdog component (using timers and fed by coroutine, no hardware wdt), uses ~1kB RAM

---------------------------------------------------
#### Version 3.7.1
* small code refactors to improve structure
* [amux] updated to support amux connected to amux

---------------------------------------------------
#### Version 3.7.0
* [config] removed possibility to use a configuration dictionary for a component, now only (kw)args are allowed
* [esp8266] possibility to use without a mounted filesystem to have 6kB more RAM, also making it possible to use 44*1024B heap safely (8kB more) --> 14kB more RAM
* [mqtt] will use Tree module if filesystem is unavailable on esp8266

---------------------------------------------------
#### Version 3.6.4
* [config] bugfix for using lists in dictionary constructor_args

---------------------------------------------------
#### Version 3.6.0
* [config] changed object creation to use constructor args as kwargs if type dict

---------------------------------------------------
#### Version 3.5.2
* added support for Multiplexer (Mux, Analog-Mux), supporting esp8266 and lobo_esp32
* added soilMoisture sensor (supports multiple sensors, connected by Amux/mux), supporting esp8266 and lobo_esp32

---------------------------------------------------
#### Version 3.5.1
* configuration now reads the version of a module (``__version__=xyz``) and logs it so debugging and version control gets easier
* bugfix in config: 0 was interpreted as False which leads to args not being recognized
* logging on esp32 prints time to repl if rtc_sync activated

---------------------------------------------------
#### Version 3.5.0
* added module to wrap around any temperature/humidity sensor only by providing a configuration (supports offset addition, precision, regular publishing of values), it's a big generic module though
* small change to config.registerComponent(): configurations can now have an empty config dictionary and put all ``constructor_args`` directly into the ``constructor_args`` list (they are looked up in config.COMPONENTS so there should be no name collision!)
* changed .sensors.htu21d to using a new sensor template (template under development) that supports precision and offset

---------------------------------------------------
#### Version 3.4.1
* better debug
* new debug module to check if device is running all the time

---------------------------------------------------
#### Version 3.4.0
* optimized login topic and payload
* bugfixes
* temporarily removed heater module until it is updated and tested

---------------------------------------------------
#### Version 3.3.1
* updated uasyncio to version 2.0, which needs 200B more (optional, works with previous version too)
* [mqtt] fixed bug registering componenets from local file on reconnection
* [config] pysmartnode version is printed on startup
* [config] fixed spelling mistake in file name of components.json

---------------------------------------------------
#### Version 3.3.0
* first version to be published to github
* changes to logging
* small bugfix in subscribe_file.py
* usable on esp82666 again with enough RAM left to run multiple components
* [config] reverted breaking change of Version 3.0.2 as optimizations made this obsolete
* small bugfixes (components using old mqtt-API)

---------------------------------------------------
#### Version 3.2.1
* more RAM optimizations
* small changes to make config dict more readable

---------------------------------------------------
#### Version 3.2.0
* [breaking change] config.json is config.py now, giving a better structure and shrinking code size
* [RAM] released 1kB of RAM through optimizations and config change

---------------------------------------------------
#### Version 3.1.3
* implemented module "subscribe_file" to save ~1kB of RAM on esp8266 by saving subscribed topics to file
* changed esp8266 build heap size 44*1024B leaves 10kB of free RAM with i2c,htu,easyGPIO,ram active. still unusable with default firmware
* changes to mqtt_as to save some ram on esp8266

---------------------------------------------------
#### Version 3.1.2:
* logging divided into modules for esp32 and esp8266
* esp8266 unusable because RAM demands are too high

---------------------------------------------------
#### Version 3.0.2:
* [breaking change] incompatible to configs from previous version
* changes in code structure
* config.id is not binary anymore
* ported to esp32 (only loboris port tested)
* log os.uname()
* switched to mqtt_as as backend module 
* mqtt module now uses tree/subscription structure for storing subscriptions and is more modular
* project named pysmartnode
* changed mqtt config message to use less memory
* local component configuration supported
* received configuration is stored locally as a backup
* mqtt api changed for subscribed callbacks
* mqtt api extended for publishing
* config module extended and optimized
* reworked all modules to support modified APIs

---------------------------------------------------
#### Version 2.2.0:
* display module added
* mqtt: convert message to dict -if possible- before calling execute()
* mqtt: catch message of exceptions thrown by functions called by execute() and log the message

---------------------------------------------------	
#### Version 2.1.3:
* ram: module does gc and publishing, without it, no gc is scheduled

---------------------------------------------------	
#### Version 2.1.2:
* mqtt: published device VERSION and STATUS (+last will) now retained
* heater: bugfix for shutting down after requested temp change if temp<target-offset, general reaction time improvement
* heater: publish status retained

---------------------------------------------------
#### Version 2.1.1:
* heater: bugfix

---------------------------------------------------
#### Version 2.1.0:
* mqtt: wildcard subscriptions (e.g. "home/#") are now possible and correctly handled
* easyGPIO module added: read/write a gpio by publishing to its topic, service activated by config
* ram module: publish free ram periodically
* heater: added START_CYCLES: temp has to be lower than target-hysterese_low for n cycles before heater starts heating (spike influence reduction)
* mqtt: last will and startup status to show controller online status; keepalive set and ping is being send automatically
* buzzer added (works similar to LEDNotification)

---------------------------------------------------
#### Version 2.0.0:
* [breaking change] config: new configuration method and structure to import and start modules according to config

---------------------------------------------------