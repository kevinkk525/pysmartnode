# Changelog

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