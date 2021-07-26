""" Main datalogger function """

import os
from machine import Pin, SoftSPI
from sdcard import SDCard

# Initialise SD Card
spisd = SoftSPI(-1, miso = Pin(13), mosi = Pin(12), sck = Pin(14))
sd = SDCard(spisd, Pin(27))
vfs = os.VfsFat(sd)
os.mount(vfs, '/sd')
os.chdir('sd')

