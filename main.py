""" Main datalogger function """

import os
from machine import Pin, SoftSPI, PWM
from sdcard import SDCard
import ads1x15

# Initialise SD Card
spisd = SoftSPI(-1, miso = Pin(13), mosi = Pin(26), sck = Pin(14))
sd = SDCard(spisd, Pin(27))
vfs = os.VfsFat(sd)
os.mount(vfs, '/sd')
os.chdir('sd')

#Text writing:
file = open('data.txt', 'a')
file.write('1,2,3,4,5')
file.close()
# csv_file = 

# Get differential values from ADC1115 (16-bit ADC)
addr = 72 # I assume the data sheet explains this
gain = 2
i2c = SoftSPI(scl=Pin(5), sda=Pin(18), freq=400000)
ads = ads1x15.ADS1115(i2c, addr, gain)
bits = ads.read(rate = 0, channel1 = 0, channel2 = 1)
voltage = ads.raw_to_v(bits)

# Run Square Wave Generator
pwm33 = PWM(Pin(33))
pwm33.freq(1000) # in Hz - really accurate as measured on oscilloscope!
pwm33.duty(512) # max = 1023 = 100%