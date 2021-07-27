""" Main datalogger function """

import os
from machine import Pin, SoftSPI
from sdcard import SDCard
# i

# Initialise SD Card
spisd = SoftSPI(-1, miso = Pin(13), mosi = Pin(26), sck = Pin(14))
sd = SDCard(spisd, Pin(27))
vfs = os.VfsFat(sd)
os.mount(vfs, '/sd')
os.chdir('sd')

#Text writing:
file = open('text.txt', 'a')
file.write('1,2,3,4,5')
file.close()
# csv_file = 