""" Main datalogger function 

In case you want to run this from the REPL:
import datalogger; datalogger.main()

if stuck in main loop:
    esptool.py --chip esp32 --port /dev/tty.usbserial-0001 --baud 115200 erase_flash
    esptool.py --chip esp32 --port /dev/tty.usbserial-0001 --baud 115200 write_flash 0x1000 /Users/Jeremy/Documents/ESP32/saved_binaries/esp32-20210623-v1.16.bin
    ampy --port /dev/tty.usbserial-0001 --baud 115200 put sdcard/sdcard.py
    ampy --port /dev/tty.usbserial-0001 --baud 115200 put ads1x15/ads1x15.py
    ampy --port /dev/tty.usbserial-0001 --baud 115200 put datalogger.py
    ampy --port /dev/tty.usbserial-0001 --baud 115200 put main.py
Not yet implemented: WiFi removal of data.
"""

import os
from machine import Pin, SoftSPI, SoftI2C, PWM
from sdcard import SDCard
import sys
import ads1x15
import time

class Logger:
    DEBUG = 10
    def isEnabledFor(self, _):
        return False
    def debug(self, msg, *args):
        pass
    def getLogger(self, name):
        return Logger()

def init_pwm(pin = 33, freq = 1000, duty_cycle = 512):
    # Run Square Wave Generator
    try:
        pwm = PWM(Pin(pin))
        pwm.freq(freq) # in Hz - really accurate as measured on oscilloscope!
        pwm.duty(duty_cycle) # max = 1023 = 100%
        led_state(state = 'ok')
        return pwm
    except Exception as e:
        led_state(state = 'pwm')
        time.sleep(1)
        init_pwm(pin, freq, duty_cycle)


def init_sd():
    # Initialise SD Card
    # https://www.youtube.com/watch?v=qL2g5YIVick
    sd = None
    while sd is None:
        try:
            spisd = SoftSPI(-1, miso = Pin(27), mosi = Pin(25), sck = Pin(26))
            sd = SDCard(spisd, Pin(33)) # cs
            
            vfs = os.VfsFat(sd)
            os.mount(vfs, '/sd') # can't mount something that's already been mounted - will trigger EPERM error
            led_state(state = 'ok')
            print('Successfully mounted SD card.')
            return sd
        except OSError as e:
            print(e)
            if str(e) == 'no SD card':
                int_state  = led_state(state = str(e))
                print(int_state)
                print(e)
                time.sleep(2) # delay to prevent needless cycling
            elif str(e) == '[Errno 1] EPERM': # it thinks it's still mounted
                """This will also be triggered if accidentally re-mounting even if there's been no 
                change in SD card connection. Bug?"""
                print('Unmounting SD card.')
                os.umount('/sd')
                int_state  = led_state(state = 'no SD card')
                print(int_state)
                time.sleep(2) # delay to prevent needless cycling
                print('Re-initialising SD...')
            elif str(e) =='[Errno 5] EIO': # input/output error?
                """Not sure what EIO means?"""
                print('Error - input/output')
                print(e)
                print('Unmounting SD card.')
                os.umount('/sd')
                int_state  = led_state(state = 'no SD card')
                print(int_state)
                time.sleep(2) # delay to prevent needless cycling
                print('Re-initialising SD...')
            else:
                print(str(e))
                int_state  = led_state(state = 'no SD card')
                print(int_state)
                time.sleep(2)
        except KeyboardInterrupt:
            sys.exit()

def init_adc(gain = 4):
    """Initialise the TI ADS1115 (16-bit ADC)
    TODO: Generalise pin assignment. """
    addr = 72 # I assume the data sheet explains this
    i2c = SoftI2C(scl=Pin(5), sda=Pin(18), freq=400000)
    ads = ads1x15.ADS1115(i2c, addr, gain)
    return ads

def init_write(column_names, filename = 'data.txt'):
    """ Initialise the new txt file. Give it appropriate column names. """
    try:
        file = open(filename, 'w')
        led_state(state = 'ok')
        file.write(column_names)
        file.close() 
        print('Successfully wrote to new file:', str(filename))
        return 0   
    except OSError as e:
        if str(e) == '[Errno 5] EIO':
            led_state(state = 'no sd card')
            time.sleep(1)
            main()
        elif str(e) == '[Errno 22] EINVAL':
            led_state(state = 'no sd card')
            time.sleep(1)
            main()

def write(data, filename = 'data.txt'):
    """ Appends to a file that already exists. 
    It also closes after each append to minimise dataloss during sudden removal. """
    try:
        file = open(filename, 'a')
        led_state(state = 'ok')
        file.write(data)
        file.close()
        return 0
    except OSError as e:
        if str(e) == '[Errno 5] EIO':
            led_state(state = 'no sd card')
            time.sleep(1)
            main()
        elif str(e) == '[Errno 22] EINVAL':
            led_state(state = 'no sd card')
            time.sleep(1)
            main()



def get_voltage(ads, channel1, channel2 = None):
    """Gets the voltage and returns it."""
    if ads == None:
        ads = init_adc()
    
    bits = ads.read(rate = 0, channel1 = channel1, channel2 = channel2)
    voltage = ads.raw_to_v(bits)
    
    return voltage

def led_state(state = 'other', pins = [15, 2, 4]):
    """The following are error lights for the user to have an idea of the error state.
    ADC-PWM-SD: 0 = normal, 1 = error
    
    You can have 8 states available:
    000 (0): 'ok' - System operating normally.
    001 (1): 'no sd card' - No SD card.
    010 (2): 'pwm' - PWM Error.
    011 (3): Not used.
    100 (4): 'adc' - ADC Error.
    101 (5): Not used.
    110 (6): 'mnfe' - Module Not Found Error. Check the imports.
    111 (7): 'on' - Other error or state not set.
    
    TODO: Generalise pin assignment.
    """
    
    state = str(state)
    state = state.lower()

    led0, led2, led4 = Pin(pins[0], Pin.OUT), Pin(pins[1], Pin.OUT), Pin(pins[2], Pin.OUT)
    led_val = []

    if state == 'ok': led_val = [0,0,0] # 000
    elif state == 'no sd card': led_val = [0,0,1] # 001
    elif state == 'pwm': led_val = [0,1,0] # 010
    elif state == 'NA': led_val = [0,1,1] # 011
    elif state == 'adc': led_val = [1,0,0] # 100
    elif state == 'NA': led_val = [1,0,1] # 101
    elif state == 'NA': led_val = [1,1,0] # 110
    else: led_val = [1,1,1] # 111
         
    led0(led_val[0]), led2(led_val[1]), led4(led_val[2])

    return int(2**0*led0.value() + 2**1*led2.value() + 2**2*led4.value()) # i.e. a number 0 - 7 for current system state

def recursion_filename(filename, i = 0, dirs = os.listdir()):
    """Keeps iterating until it finds a free filename. This prevents overwrites."""
    
    if filename in dirs:
        i += 1
        filename = filename.strip('.txt')
        filename += str(i) + '.txt'
        return recursion_filename(filename, i, dirs)
    else:
        return filename

def check_filename(filename, folder = '/'):
    """Preconditions the filename to remove anything extraneous."""
    pass
    return recursion_filename(filename, i = 0, dirs = os.listdir(folder))

def unique_file(basename, ext, folder = '/'):
    
    actualname = "%s.%s" % (basename, ext)
    print(actualname)
    i = 0
    try:
        while actualname in os.listdir(folder):
            i += 1
            actualname = "%s%d.%s" % (basename, i, ext)
        return actualname
    except OSError as e:
        if str(e) == '[Errno 5] EIO':
            main() # reboot program on error with filename
def main():
    sd = None
    sd = init_sd()
    if sd is None: main()
    int_state = led_state(state = 'ok', pins = [15, 2, 4])
    pwm = init_pwm(pin = 32, freq = 1000, duty_cycle=512)
    
    adc = init_adc()

    filename = unique_file(basename = 'data', ext = 'txt', folder = 'sd') # checks if this filename exists. If so, increment by 1 to prevent overwrite.
    filename = 'sd/' + filename
    
    log_file = 'log.txt' # Not used as yet. TODO: Implement logger output for debugging.

    # Initialise new datataking file.
    column_names = 'Time (s), A0-A1 (mV), A2-A3 (mV) \n' # 'A2-A3 (mV)'
    init_write(column_names = column_names, filename = filename)

    # Start taking measurements.
    start_time = time.time()
    last_measurement = time.time()
    voltages0, voltages1 = [], []
    while True: 
        if (time.time() - last_measurement) < 1:
            voltage0 = get_voltage(adc, channel1 = 0, channel2 = 1)*1000 # convert to mV
            voltages0.append(voltage0) # Not great for micropython to have evergrowing lists. But it should be very short and prevent overflow.
            voltage1 = get_voltage(adc, channel1 = 2, channel2 = 3)*1000 # convert to mV
            voltages1.append(voltage1)
        else:
            # This could be moved to a separate thread.
            time_since_start = str(time.time() - start_time)
            lenv0, lenv1 = len(voltages0), len(voltages1)
            
            if lenv0 <=1: lenv0 = 1 # just in case it fails to take a reading.
            if lenv1 <=1: lenv1 = 1
            
            average_voltages0 = str(sum(voltages0) / lenv0)
            average_voltages1 = str(sum(voltages1) / lenv1)

            data = str(time_since_start + ',' + average_voltages0 + ',' + average_voltages1 + '\n')
            write(data = data, filename = filename)
            print(data)
            last_measurement = time.time()
            led_state('other')
            voltages0, voltages1 = [], []

if __name__ == '__main__':
    """ To be implemented. Maybe in boot.py? """
    # main()
    pass