import time
import os
import board
import displayio
import terminalio
import busio
from digitalio import DigitalInOut
from analogio import AnalogIn
import neopixel
import adafruit_adt7410
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from adafruit_button import Button
import adafruit_touchscreen
import adafruit_logging as logging
import adafruit_pyportal
from adafruit_minimqtt import MQTT

# ------------- WiFi ------------- #

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# ------- Sensor Setup ------- #
# init. the temperature sensor
i2c_bus = busio.I2C(board.SCL, board.SDA)
adt = adafruit_adt7410.ADT7410(i2c_bus, address=0x48)
adt.high_resolution = True
temperature = "blaa"
# init. the light sensor
light_sensor = AnalogIn(board.LIGHT)

# init. the motion sensor
movement_sensor = DigitalInOut(board.D3)

button1_state = 0
button2_state = 0

# ------------- Screen eliments ------------- #

display = board.DISPLAY


def set_backlight(val):
    """Adjust the TFT backlight.
    :param val: The backlight brightness. Use a value between ``0`` and ``1``, where ``0`` is
                off, and ``1`` is 100% brightness.
    """
    val = max(0, min(1.0, val))
    board.DISPLAY.auto_brightness = False
    board.DISPLAY.brightness = val

ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(320, 240))

# Load the font
font = terminalio.FONT

DISPLAY_STRING = "Button Text"

# Make the display context
splash = displayio.Group(max_size=200)
board.DISPLAY.show(splash)
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 100
BUTTON_MARGIN = 10

buttons = []
# Default button styling:

# a roundrect
button_1 = Button(x=BUTTON_MARGIN, y=BUTTON_MARGIN,
                  width=BUTTON_WIDTH, height=BUTTON_HEIGHT,
                  label="Button 1", label_font=font, label_color=0x0000FF,
                  fill_color=0x00FF00, outline_color=0xFF0000)
buttons.append(button_1)

# a shadowrect
button_2 = Button(x=BUTTON_MARGIN, y=BUTTON_MARGIN*2+BUTTON_HEIGHT,
                  width=BUTTON_WIDTH, height=BUTTON_HEIGHT,
                  label="Button 2", label_font=font, label_color=0x0000FF,
                  fill_color=0x00FF00, outline_color=0xFF0000)
buttons.append(button_2)

for b in buttons:
    splash.append(b.group)

temperature_label = Label(terminalio.FONT, text="temperature", color=0x0000FF, max_glyphs=40)
# Set the location
temperature_label.x = 200
temperature_label.y = 10
splash.append(temperature_label)

light_label = Label(terminalio.FONT, text="lux", color=0x0000FF, max_glyphs=40)
# Set the location
light_label.x = 200
light_label.y = 30
splash.append(light_label)

feed1_label = Label(terminalio.FONT, text="MQTT feed", color=0x0000FF, max_glyphs=40)
# Set the location
feed1_label.x = 200
feed1_label.y = 100
splash.append(feed1_label)

feed2_label = Label(terminalio.FONT, text="MQTT feed2", color=0x0000FF, max_glyphs=40)
# Set the location
feed2_label.x = 200
feed2_label.y = 130
splash.append(feed2_label)

# ------------- Topic Setup ------------- #

# MQTT Topic
# Use this topic if you'd like to connect to a standard MQTT broker
mqtt_topic = 'test/topic'
mqtt_temperature = 'pyportal/temperature'
mqtt_lux = 'pyportal/lux'
mqtt_PIR = 'pyportal/pir'
mqtt_sound = 'pyportal/sound'
mqtt_button1 = 'pyportal/button1'
mqtt_button2 = 'pyportal/button2'
mqtt_feed1 = 'pyportal/feed1'
mqtt_feed2 = 'pyportal/feed2'

# ------------- Code ------------- #

# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connect(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print('Connected to MQTT Broker!')
    print('Flags: {0}\n RC: {1}'.format(flags, rc))

def disconnected(client, userdata, rc):
    # This method is called when the client is disconnected
    print('Disconnected from MQTT Broker!')

def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print('Subscribed to {0} with QOS level {1}'.format(topic, granted_qos))

def publish(client, userdata, topic, pid):
    # This method is called when the client publishes data to a feed.
    print('Published to {0} with PID {1}'.format(topic, pid))

# Connect to WiFi
wifi.connect()

# Set up a MiniMQTT Client
client = MQTT(socket,
            broker = secrets['broker'],
            port = 1883,
            username = secrets['user'],
            password = secrets['pass'],
            network_manager = wifi)

# Connect callback handlers to client
client.on_connect = connect
client.on_disconnect = disconnected
client.on_subscribe = subscribe
client.on_publish = publish

print('Attempting to connect to %s' % client.broker)
client.connect()

print('Subscribing to %s and %s' % (mqtt_feed1, mqtt_feed2))
client.subscribe(mqtt_feed1)
client.subscribe(mqtt_feed2)

while True:
    # Poll the message queue
    client.loop()

    # Send a new message
    light_value = light_sensor.value
    light_label.text = 'Light Sensor: {}'.format(light_value)
    temperature = adt.temperature
    temperature_label.text = 'Temp Sensor: {}'.format(temperature)
    movement_value = movement_sensor.value

    feed1_label.text = 'MQTT Feed1:'
    feed2_label.text = 'MQTT Feed2:'

    touch = ts.touch_point
    if touch:
        for i, b in enumerate(buttons):
            if b.contains(touch):
                print('Sending button%d pressed' % i)
                if i == 0:
                    button1_state = 1
                if i == 1:
                    button2_state = 1
                b.selected = True
            else:
                if i == 0:
                    button1_state = 0
                if i == 1:
                    button2_state = 0
                b.selected = False

    print('Sending light sensor value: %d' % light_value)
    client.publish(mqtt_lux, light_value)

    print('Sending temperature value: %d' % temperature)
    client.publish(mqtt_temperature, temperature)

    print('Sending motion sensor value: %d' % movement_value)
    client.publish(mqtt_PIR, "movement_value")

    print('Sending button 1 state: ')
    client.publish(mqtt_button1, button1_state)

    print('Sending button 2 state: ')
    client.publish(mqtt_button2, button2_state)

    time.sleep(0.5)