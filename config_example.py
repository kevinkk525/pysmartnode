from sys import platform
from micropython import const

# Required custom configuration
WIFI_SSID = "SSID"
WIFI_PASSPHRASE = "PASSPHRASE"
MQTT_HOST = "BROKER-IP"
MQTT_USER = ""
MQTT_PASSWORD = ""

# Optional configuration
MQTT_KEEPALIVE = const(60)
MQTT_HOME = "home"
MQTT_RECEIVE_CONFIG = True
MQTT_TYPE = const(0)  # 0 = mqtt client, 1 = miropython_iot as proxy (experimental)
# RECEIVE_CONFIG: Only use if you run the "SmartServer" in your environment which
# sends the configuration of a device over mqtt
# If you do not run it, you have to configure the components locally on each microcontroller

if platform == "esp32_LoBo":
    MDNS_ACTIVE = True
    MDNS_HOSTNAME = "esp32"
    MDNS_DESCRIPTION = "esp32_mdns"
    FTP_ACTIVE = True
    TELNET_ACTIVE = True
    RTC_SYNC_ACTIVE = True
    RTC_SERVER = "de.pool.ntp.org"
    RTC_TIMEZONE = "CET-1CEST,M3.5.0,M10.5.0/3"  # Germany, taken from MicroPython_BUILD/components/micropython/docs/zones.csv
elif platform == "esp8266":
    LIGTWEIGHT_LOG = True  # uses a smaller class for logging on esp8266 omitting module names, saves ~500Bytes
    MQTT_MINIMAL_VERSION = True  # saves ~200B if used as frozen bytecode
    USE_SOFTWARE_WATCHDOG = False  # uses ~700B of RAM, started with timeout=2xMQTT_KEEPALIVE, use if you experience outages
    RTC_SYNC_ACTIVE = False  # uses ~600B additional RAM on esp8266
    RTC_TIMEZONE_OFFSET = const(2)  # offset from GMT timezone as ntptime on esp8266 does not support timezones

# 10min, Interval sensors send a new value if not specified by specific configuration
INTERVAL_SEND_SENSOR = const(600)

# Does not need to be changed normally
DEBUG = False
DEBUG_STOP_AFTER_EXCEPTION = False
