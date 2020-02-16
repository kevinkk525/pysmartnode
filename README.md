# Micropython SmartHome Node

This repository provides a general framework to deploy smarthome nodes based on micropython and communicating using mqtt.
The framework is easy to use and extend with custom components/scripts.

## Why another framework?

Many SmartHome frameworks are based on C(++) which makes extending them more difficult. 
In micropython environment there are a lot less frameworks and often have a difficult documentation or None and are either complex or do not have enough features.
So I decided to build one myself with the following points in mind:

* This framework aims to be easy to use and easy to extend with custom scripts and components.
* The documentation should be easy to understand and as short as possible while still giving a clear path of how to use the project and integrate your components.
* The project structure should be easily understandable, no guessing which files are loaded when and by what
* Providing templates as example and help of how to make new components, etc.
* Be reliable (Have a reliable connection using mqtt, do not fail if a component fails, ...)
* Comment as much as possible so that anyone can understand what a file or configuration option is for


## 1.Hardware

The project is tested on ESP32 and ESP8266 microcontrollers.
It also supports the unix port. 

### ESP8266

The ESP8266 works reliable and resilient and is useable 24/7 as it recovers from any crashes/freezes using a software watchdog. Before micropython 1.11 there was a bug that could freeze uasyncio for 1h 11min that made the software watchdog neccesary.  
The device doesn't have much RAM but it's enough for multiple bigger components and many small ones. 

### ESP32

Official ESP32 port is supported since version 4.1.0 and loboris fork is now official unsupported since there hasn't been any commit in over 7 months. 
However no code for loboris fork has been removed and even the updated modules are written to be compatible, I just don't test any features on that platform myself anymore. 

In recent tests this hardware has shown to be finally resilient and can be used 24/7.

### Unix port

Since version 5.0.0 the unix port is supported. There are no calls to *machine* or *network* in the base code of the framework. 
The usable components are limited at the moment as no GPIO support is available. However system calls work which gives a lot of options,
e.g. to use the raspberry-remote library to control RF433Mhz devices.
Basic GPIO support is planned to be implemented but will still be slow and not a C-module. 


## 2.Getting started

### 2.1. Program files

To clone this repository run
```
git clone https://github.com/kevinkk525/pysmartnode
cd pysmartnode
git submodule update --init --recursive --remote
```

To update run inside the repository directory
```
git pull
git submodule update --recursive --remote
```
You should have the latest micropython firmware and include the directory "pysmartnode" as frozen bytecode into your firmware. (Put it in the "module" directory before building the firmware)
On ESP32 frozen bytecode is not neccessary but should be considered if not using psram.

#### Warning
Many modules use Variable Annotations ([PEP526](https://www.python.org/dev/peps/pep-0526/)) but micropython doesn't support
[PEP 526 (Syntax for Variable Annotations)](https://github.com/micropython/micropython/issues/2415#issuecomment-548173512) yet.
<br> This means that every build, .mpy or directly uploaded file with variable annotations will fail.
<br> To work around this problem, the files have to be stripped of their variable annotations. This can be done with the python module "strip-hints".

<br> In tools there is a [script](./tools/esp8266/esp8266_remove_hints.sh) that will replace all files with varibale annotations with a stripped version of the file.
<br> Use that script after syncing/copying the files in the modules directory before building the
firmware. You have to adapt the path in the script, so you could point it to any directory, doesn't
 need to be the esp8266 modules directory.

Alternatively a prebuilt firmware for the esp8266 can be used that should be attached to every release on github. On esp32 the precompiled .mpy files can be used that are also attached to every github release.
<br> Then it is not neccesary to strip the source files of hints.
<br> This is recommended because the esp8266 needs a custom firmware build anyway as it can't compile the project because of its small RAM.
<br>The esp32 could build the project but that is very slow and therefore it is recommended to use .mpy files.

### 2.2. Dependencies

Required external modules are:

* uasyncio (>=V2.0) (if not already part of the firmware)
* micropython-mqtt-as, my own fork that has some needed features: ([mqtt_as](https://github.com/kevinkk525/micropython-mqtt))

All required modules are in this repository and don't need to be aquired manually. 
Just put the directories `micropython_mqtt_as` and `uasyncio` from `external_modules` into your `modules` directory before building the firmware or run the correct script in section `Tools`.
The *micropython_mqtt_as* directory is a submodule to my repository so this will be updated automatically.
Uasyncio is copied from the official repository and I will update the file as soon as a new version is published.

## 3. Components
The included components can be found in the directory "pysmartnode/components".
<br>Their description and configuration will soon be added to the wiki but for now you can check the files itself.
<br>They contain an example configuration of the component and some description.
The example configuration however is in [hjson](https://github.com/hjson/hjson-py), which is easier than *json* and has the possibility to have comments in it.
This format is used in the *SmartServer* (see 4.1.), if you want to put the configuration onto your controller, you have to convert it to json.

Every loaded component will be published as *log.info* to "<home>/log/info/<device_id>" with the version of the module.

### API

Components can be and do anything. There is a basic API and [base class](./pysmartnode/utils/component/__init__.py) which helps with homeassistant mqtt discovery and the basic API.
<br>Sensors all have a similar API to have a standardized usage through the [sensor base class](./pysmartnode/utils/component/sensor.py).
The sensor base class makes developing sensors very easy as it takes care of mqtt discovery, reading and publishing intervals and the standardized API.
All sensors now have a common API:
- getValue(sensor_type)->sensor_type last read value
- getTopic(sensor_type)->mqtt topic of sensor_type
- getTemplate(sensor_type)->homeassistant value template of sensor_type
- getTimestamp(sensor_type)->timestamp of last successful sensor reading
- getReadingsEvent()->Event being set on next sensor reading

<br>Sensor_types in definitions but can be custom, those are only the ones supported by Homeassistant.

<br>Common features:
- Reading interval and publish interval separated and not impacting each other
- Reading and publish intervals can be changed during runtime, optionally by mqtt
- Sensor subclass only needs to implement a _read() function reading the sensor and submitting the read values. Base class does everything else (publishing, discovery, ...)

<br>This should make working with different types of sensors easier. If you are e.g. building a heating controller and need a temperature from some sensor, you can just connect any sensor and provide the heating code with that sensor by configuration.
<br>Switch components can be integrated similarily easy using the [switch base class](./pysmartnode/utils/component/switch.py).
<br>Templates for how to use the components can be found in [templates](./_templates).

### MQTT-Discovery

[Home-Assistant](https://www.home-assistant.io/) has the feature to automatically discover mqtt components if they provide the needed configuration using mqtt. 
Since version 5.0.0 all components can now make use of the [MQTT-Discovery](https://www.home-assistant.io/docs/mqtt/discovery/).

### Component-Template

To make building new components easier, there is a [template](./_templates/component_template.py).
It should help understanding how the configuration can be read and mqtt subscriptions and publishing values works.

Besides the general components, components can mostly be divided in sensors and switches, which have a slightly different API.
There are templates for both types of components, [sensors](./_templates/sensor_template.py) and [switches](./_templates/switch_template.py).
There is also a [Pushbutton template](./_templates/button_template.py) which is just a simpler version of the switch.

## 4.Configuration

To run the pysmartnode on boot, just use the included "main.py".

The environment specific configuration is done within the "config.py" file that has to be put in the root directory of your microcontroller (or if frozen in "modules"). Copy the "config_example.py" to "config.py" and change it according to your needs.
In this file you have to specify the WIFI and MQTT parameters of your home environment.
There are also some optional parameters to configure base modules and behaviour.

### Project configuration

The project configuration is done in the file *config.py* which should be created by copying the [config_example.py](./config_example.py) as *config.py*.
If you have a filesystem, copy it onto the device or put it as frozen bytecode in your modules directory.

In *config.py* only those configurations have to be provided, that overwrite the default values found in [config_base](./pysmartnode/config_base.py).

The basic configuration options are:
* WIFI: SSID and PASSPHRASE
* MQTT: HOST, PORT, USER and PASSWORD

Optional configurations for the network are:
* MQTT_KEEPALIVE: the keepalive interval, if the device does not send a ping within this interval, it will be considered offline
* MQTT_HOME: the mqtt root topic
* MQTT_AVAILABILITY_SUBTOPIC: the subtopic used to publish the availability state. Used for last will too. Will generate MQTT_HOME/<device-id>/MQTT_AVAILABILITY_SUBTOPIC
* MQTT_DISCOVERY_PREFIX: the discovery prefix configured in home-assistant, see [autodiscovery](https://www.home-assistant.io/docs/mqtt/discovery/).
* MQTT_DISCOVERY_ENABLED: disable mqtt discovery if you don't want to use it or don't use home-assistant.
* MQTT_RECEIVE_CONFIG: if the device should receive its configuration using mqtt subscription. This only works when using [SmartServer](https://github.com/kevinkk525/SmartServer) in your network
* MQTT_TYPE: support for an experimental connection type (will be described when fully tested, documented and implemented). Not working at the moment.
* WIFI_LED: Set option to a pin number to use the connected LED to display the Wifi status. If the initial connect to the WIFI was successful then it will blink 5 times very quickly. While connected it will blink quickly one time every 30 seconds. When not connected it will make 3 long blinks every 5 seconds.
* WIFI_LED_ACTIVE_HIGH: Set to False if the connected LED is active low.
* WEBREPL_ACTIVE: Starts the webrepl from pysmartnode scripts without modifying the boot.py, also intializes the webrepl so calling "webrepl_setup" is not needed.
* WEBREPL_PASSWORD: Set a password for the webrepl.

Platform dependent options are
- for esp32_LoBo:
    * MDNS_ACTIVE, MDNS_HOSTNAME, MDNS_DESCRIPTION: mdns options
    * FTP_ACTIVE: enable the built-in ftp server, very nice to have
    * TELNET_ACTIVE: enable the built-in telnet server to access the repl over wifi
    * RTC_SYNC_ACTIVE, RTC_SERVER, RTC_TIMEZONE: enable RTC time sync, set the time server and timezone
- for esp32 (official port):
    * FTP_ACTIVE: FTP server from [Robert](https://github.com/robert-hh/FTP-Server-for-ESP8266-and-ESP32)
    * RTC_SYNC_ACTIVE: if RTC time sync should be done
    * RTC_TIMEZONE_OFFSET: as esp32 does not support timezones, add your offset here to match your time
- for esp8266:
    * LIGHTWEIGHT_LOG: if a logging module with less RAM demands should be used (saves ~500B depending on the amount of log objects as it doesn't create module specific objects) but doesn't send module names in the log
    * RTC_SYNC_ACTIVE: if RTC time sync should be done (saves ~600B)
    * RTC_TIMEZONE_OFFSET: as esp8266 does not support timezones, add your offset here to match your time
    * USE_SOFTWARE_WATCHDOG: Needed for micropython versions before 1.11 as uasyncio could get stuck for 1h 11minutes but not the interrupts. This makes using a software watchdog possible to reset hanging units (uses ~600B)
    * WIFI_SLEEP_MODE: Sleep mode by default disabled (in mqtt_as) to improve esp8266 wifi stability. No need to change it.
- for unix port:
    * RTC_SYNC_ACTIVE: use synced time. Only disable if the underlying OS has no internet access and can't sync its time. Micropython doesn't sync the time on unix. 

A few additional options define some constants:
* INTERVAL_SENSOR_PUBLISH: defines the interval in which sensors are publishing their value if no interval is provided in the component configuration
* INTERVAL_SENSOR_READ: defines the interval in which sensors are read if configuration is not provided by the component.
* DEVICE_NAME: set to a unique device name otherwise the device id will be used. This is relevant for homeassistant mqtt autodiscovery so the device gets recognized by its device_name instead of the id. It is also used with the unix port instead of the unique chip id (which is not available on the unix port) and it therefore has to be UNIQUE in your network or it will result in problems.
* DEBUG: Will display additional information, useful for development only
* DEBUG_STOP_AFTER_EXECUTION: normally if an uncatched exception occurs and the loop exits, it will reset the device and the message will be logged after restart. This disables it and will stop at the repl after the exception.

### Component configuration
The configuration of all components used on a microcontroller can be configured in two different ways:

#### 4.1. Using SmartServer
To configure the used components it is possible to run [SmartServer](https://github.com/kevinkk525/SmartServer) in your network, which holds the configuration of each microcontroller and publishes it over MQTT when requested.
This makes it very easy to change configurations but makes the SmartHome less secure as the configuration is not fixed on the device itself.
The received configuration is stored locally to be able to recover from power outages even if the SmartServer is offline. For storing offline the method 3.1.2.1. is used on the ESP32 and 3.1.2.2. is used on the ESP8266 as these are the preffered methods.
Another benefit of using the SmartServer is that it collects the log messages that this framework publishes over MQTT.


#### 4.2. Using local configuration components.py
Local configuration is only used if either no configuration could be received from the SmartServer or receiving the configuration is disabled.
<br>This configuration can be used if you plan on freezing the component configuration or do not have a filesystem activated to save some RAM.
<br>If the *components.py* module has a *COMPONENTS* dictionary, this will be used just like the received dictionary from SmartServer.
Don't save it as a .json string but as a python dictionary.

Alternatively you can use this module to register components as you see fit or add your own functions to the asyncio loop.
See the template for the components.py file in the template directory [here](./_templates/components.py).

#### 4.3. Configuration options

The basic configuration options of a component are when using SmartServer or COMPONENTS dictionary in components.py:
* package:                  The python package location, the "." means that it is in *pysmartnode.components*
* component:                The component is the class name or function/coroutine name. A component started by a function is called a "service"
* constructor_args:         These are the arguments for the constructor of the component class or function/coroutine. It can be a dictionary or a list but a dictionary is preferred as it makes the configuration more readable.


## 5. Tools

The tools directory contains a lot of scripts I use to synchronize the project files with the build directory of the microcontroller and for building and flashing firmwares.
They are heavily specialized to my environment (my home path e.g.). These can be run in a linux shell (windows wsl too).
I'm not that skilled in making these very generally usable but I keep them in the repository in case someone finds them useful or even contributes better ones. (Would be very happy about that!)

## 6. Structure overview

A small overview of the directory structure:

 * /:                   contains a modified boot.py usable on esp8266 and esp32, the project configuration file, ...
 * _templates:          contains templates for building own scripts/components/config.. not to be uploaded to the device
 * _testing:            contains tests of some modules, not needed on the device
 * dev:                 contains modules that are in development and either contain bugs, are not functional yet or just experimental
 * external_modules:    contains the needed external modules like mqtt_as and uasyncio. Can be ignored if the dependencies of this project are available.
 * pysmartnode :        contains the project files, the configuration library and main startup script
    * components:       contains all the component libraries grouped by type
        * devices:      libraries for controlling external devices (displays, heater, arduino, ...)
        * machine:      libraries for controlling the device (gpio, watchdog, ...)
        * multiplexer:  all sorts of multiplexer: mux, analog-mux, passthrough-mux (analog-mux used as digital passthrough)
        * sensors:      all kinds of externally connected sensors
        * switches:     components that can be turned on/off (buzzer, led, gpio, ...)
        * unix:         components that can only be used with the unix port
    * libraries:        contains general device libraries not specific to pysmartnode
    * logging:          logging implementations sending log messages over mqtt
    * networking:       wifi and mqtt handling
    * utils:            base classes, helping functions, decorators and wrappers. May be helpful in some custom components. Example: asyncio Event class
        * component:                basic component classes
        * wrappers:                 wrappers for all sorts of things
        
## 7. Project Flowchart

I'd like to provide a small flowchart which makes it easier to understand how this project works and which file is called when.
It shows which modules are imported by which files first (as some are imported in different files of course) in a temporal flow. Only the most important modules are shown, not util modules.

![flowchart](./file_flowchart.jpg)


## 8. Contributors

* **Kevin Köck** - *Author* 

## 9. License

This project is licensed under the MIT License - see the [LICENSE.md](./LICENSE.md) file for details.

## 10. Acknowledgments

* Thanks to Peter Hinch for providing *mqtt_as* and all cooperation on mqtt and network communication
* Thanks to anyone whose code was an inspiration
