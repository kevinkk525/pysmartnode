# Component Classes
Overview over the basic component classes and their methods.

## ComponentBase
This is the base class for all component implementations.

It provides the basic API and integration into mqtt (e.g. discovery) and helper functions.
There is a [template](./_templates/component_template.py) demonstrating how to implement a custom Component inheriting from the ComponentBase class.

### def `__init__`(self, component_name, version, unit_index: int, discover=True, logger=None, **kwargs):
|args|type|required|description|
|--|--|--|--|
|component_name|str|true|Name of the component. Will be logged.|
|version|str|true|Version of the component. Will be logged.|
|unit_index|int|true|Index of current component instance. First instance of e.g. PushButton has index 0, the next instance index 1, etc. Used for automatic topic and name generation.|
|discover|bool|false|Configures if the component should send mqtt discovery messages to get added to Home-Assistant|
|logger|object|false|The logger object for the current component instance. It is typically created in the module or on object creation. If not given, one will automatically be created using the component_name and unit_index.

### async def removeComponent(component):
Completely remove a component. It will be unregistered and also removed from Home-Assistant (if it was created using discover=True). All subscribed mqtt topics of this component will be unsubscribed.
This function can be called directly and either with a component object or with a component_name as argument, e.g. like `ComponentBase.removeComponent("PushButton0")`
The removal of a component will be logged.

### async def _remove(self):
Internal coroutine that handles the removal of the component as described for the coroutine *removeComponent()*.
Can be subclassed to extend the functionality, e.g. to stop all running tasks of the component.

### async def _init_network(self):
Logs the component module, version and name. Also sends the mqtt discovery message if enabled.
The coroutine can be subclassed to extend the functionality, e.g. to restore a certain state after the discovery message has been sent.
**Note:**  All components execute this coroutine in one asyncio Tasks sequencially. This means that waiting times will delay the execution of the *_init_network* coroutine of the next component.

### async def _discovery(self, register=True):
This coroutine has to be implemented in the subclass. Its function is to send the mqtt discovery message for Home-Assistant. If register==False it has to send an empty message, which removes the component from Home-Assistant.
The subclass can use two helper functions for publishing and deleting the discovery messages: ComponentBase._publishDiscovery and ComponentBase._deleteDiscovery.

### [TODO: some internal functions ommited for now, will add later]

### checkSensorType(obj, sensor_type):
Checks if the given object is of instance *ComponentSensor* and if it provides the *sensor_type* (e.g. temperature, humidity, ...). If a check fails, it'll raise a TypeError.

### checkSwitchType(obj):
Checks if the given object is of instance *ComponentSwitch*. If the check fails, it'll raise a TypeError.

## ComponentSensor
It provides the basic API for all sensors. It inherits from the *ComponentBase* class, which means that all methods of *ComponentBase* are available.

There is a [template](./_templates/sensor_template.py) demonstrating how to implement a custom Sensor Component inheriting from the ComponentSensor class.

### def `__init__`(self, component_name, version, unit_index, interval_publish=None, interval_reading=None, mqtt_topic=None, expose_intervals=False, intervals_topic=None, publish_old_values=False, **kwargs):
***Note:*** This class inherits from the *ComponentBase* class. The constructor arguments of the *ComponentBase* class can be used too because they are being forwarded to the base class by ***kwargs*.
|args|type|required|description|
|--|--|--|--|
|component_name|str|true|Name of the component. Will be logged.|
|version|str|true|Version of the component. Will be logged.|
|unit_index|int|true|Index of current component instance. First instance of e.g. PushButton has index 0, the next instance index 1, etc. Used for automatic topic and name generation.|
|interval_publish|float|false|How often a sensor reading should be published. If not given, defaults to *config.INTERVAL_SENSOR_PUBLISH*. Can be set to *-1* to disable publishing of readings.
|interval_reading|float|false|How often the sensor should be read. If not given, defaults to *config.INTERVAL_SENSOR_READ*. Can be set to -1 to disable the automatic reading of the sensor.
|mqtt_topic|str|false|Custom mqtt_topic for sensor reading publications. If not given, one will automatically be created using the *component_name* and *unit_index*. However, every added sensor_type can have its own mqtt topic (e.g. temperature and humidity can be published to different mqtt topics).
|expose_intervals|bool|false|The reading and publication intervals can be exposed to mqtt so they can be changed by a single message to the topic configured in *intervals_topic*.
|intervals_topic|str|false|If *expose_intervals* is enabled, this topic will be subscribed for change requests about the reading and publication intervals. Note: A topic ending with */set* is required. If no topic is given, one will be generated according to this pattern: `<home>/<device-id>/<component_name><_unit_index>/interval/set` unless the method *_default_name()* has been overwritten by the subclass. Check the repl output when running for the first time, it will print the topic which is being used.
|publish_old_values|bool|false|Typically the value being published is up-to-date and a publication is being canceled, if it can't finish until the next reading is done. This way there will always be an up-to-date value published. But if the reading interval is so low, that the publication takes longer than the reading, this would result in all publications being canceled. Setting *publish_old_values* to *true* allows the publication to finish, even if new values are available.
|**kwargs|any|false|Allows setting kwargs of the *ComponentBase* class, e.g. *discover=False*. This allows the ComponentBase class to be extended in the future without requiring all subclasses to implement the new constructor arguments. It also keeps the constructors of subclasses cleaner and easier to read.

### [TODO: describe remaining sensor methods]

## ComponentSwitch
It provides the basic API for all switches. All components that provide an interface for enabling/disabling (turning on/off) can be described as *Switches*.
It inherits from the *ComponentBase* class, which means that all methods of *ComponentBase* are available.

There is a [template](./_templates/switch_template.py) demonstrating how to implement a custom Switch Component inheriting from the ComponentSwitch class.

### def `__init__`(self, component_name, version, unit_index, mqtt_topic=None,  instance_name=None, wait_for_lock=True, restore_state=True,   friendly_name=None, initial_state=None, **kwargs):
***Note:*** This class inherits from the *ComponentBase* class. The constructor arguments of the *ComponentBase* class can be used too because they are being forwarded to the base class by ***kwargs*.
|args|type|required|description|
|--|--|--|--|
|component_name|str|true|Name of the component. Will be logged.|
|version|str|true|Version of the component. Will be logged.|
|unit_index|int|true|Index of current component instance. First instance of e.g. PushButton has index 0, the next instance index 1, etc. Used for automatic topic and name generation.|
|mqtt_topic|str|false|Custom mqtt_topic for state change requests and state publications. If not given, one will automatically be created according to this pattern: `<home>/<device-id>/<component_name><_unit_index>/set`as the command topic and without */set* at the end as the state_topic. Note that any of those topics can be used, the other one will be converted automatically.
|instance_name|str|false|A unique name for the component instance. If not given, one will automatically be created using the *component_name* and *unit_index*. However, because the *unit_index* is a dynmic value depending on the components registered, the instance_name can change when the configuration for the registered components changes. This can be undesired as it results in a different registration in Home-Asssitant.
|wait_for_lock|bool|false|If enabled, every request will wait until it acquires the lock. This way no request will get lost, even if a previous request is still being executed. If disabled, a request will be ignored if the lock is unavailable.
|restore_state|bool|false|Restore the device state which is stored by the mqtt broker as a retained message on the state topic of the component. This is usually preferred because it restores the device to its former state after a reset.
|friendly_name|str|false|A friendly name for the Home-Assistant GUI. Has no other function.
|initial_state|bool|false|Provides the initial state of a device after a reset. If not given, the first state change request will assume that the device is not in the requested state (e.g. "ON" request will assume device is currently "OFF"). In the subclass for a device the initial state could be obtained correctly (e.g. by reading a pin state) and then correctly passed on to the base class constructor.
|**kwargs|any|false|Allows setting kwargs of the *ComponentBase* class, e.g. *discover=False*. This allows the ComponentBase class to be extended in the future without requiring all subclasses to implement the new constructor arguments. It also keeps the constructors of subclasses cleaner and easier to read.

### [TODO: describe remaining switch methods]

## ComponentButton
It provides the basic API for all buttons. A button can be described a *PushButton* that has only a single-shot action on activation. It is basically a *Switch* that turns itself off directly after being switched on. It therefore inherits from the *ComponentSwitch* class, which means that all methods of *ComponentSwitch* and *ComponentBase* are available.

There is a [template](./_templates/switch_button.py) demonstrating how to implement a custom Button Component inheriting from the ComponentSwitch class.

### def `__init__`(self, component_name, version, unit_index, wait_for_lock=False, initial_state=False, **kwargs):
***Note:*** This class inherits from the *ComponentSwitch* and the *ComponentBase* class. The constructor arguments of the both classes can be used too because they are being forwarded to the base classes by ***kwargs*.
The *ComponentButton* class does not provide any new constructor arguments but has different default parameters.
|args|type|required|description|
|--|--|--|--|
|component_name|str|true|Name of the component. Will be logged.|
|version|str|true|Version of the component. Will be logged.|
|unit_index|int|true|Index of current component instance. First instance of e.g. PushButton has index 0, the next instance index 1, etc. Used for automatic topic and name generation.|
|wait_for_lock|bool|false|Same as *ComponentSwitch*. Defaults to *false* so a single-shot action is not activated again after it has finished if two activation requests were received while the action was being done.
|initial_state|bool|false|Same as *ComponentSwitch*. Defaults to *false* because a *PushButton* is "off" by default and only shortly "on" on activation.
|**kwargs|any|false|Allows setting kwargs of the base classes, e.g. *discover=False*. This allows all base classes to be extended in the future without requiring all subclasses to implement the new constructor arguments. It also keeps the constructors of subclasses cleaner and easier to read.

### async def on(self):
Turns the button on/starts the single-shot action. The state "ON" will be published on activation and once the action is finished, the state "OFF" will be published. Publications are done in a separate task and don't impact the functionality of the button, even if the network is unavailable.

### async def off(self):
Purely for compatibility, only returns *True*.

### async def toggle(self):
Always calls *self.on()*.
