"""Basic diagnostic to see if the device is working.

Usage: """

from machine import Pin
led = Pin(2, Pin.OUT)
led.on()
led.off()