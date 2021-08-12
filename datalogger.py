""" Main datalogger function 

In case you want to run this from the REPL:
import datalogger; datalogger.main()

Not yet implemented: WiFi removal of data.
"""

import os
from machine import Pin, SoftSPI, SoftI2C, PWM
from sdcard import SDCard
import sys
import ads1261evm
import time
import utime

class Logger:
    DEBUG = 10
    
    def isEnabledFor(self, _):
        return False
    
    def debug(self, msg, *args):
        pass
    
    def getLogger(self, name):
        return Logger()


def init_pwm(pin=33, freq=1000, duty_cycle=512):
    # Run Square Wave Generator
    try:
        pwm = PWM(Pin(pin))
        pwm.freq(freq) # in Hz - really accurate as measured on oscilloscope!
        pwm.duty(duty_cycle) # max = 1023 = 100%
        led_state(state='ok')
        return pwm
    except Exception:
        led_state(state='pwm')
        time.sleep(1)
        init_pwm(pin, freq, duty_cycle)


def init_sd():
    # Initialise SD Card
    # https://www.youtube.com/watch?v=qL2g5YIVick
    sd = None
    while sd is None:
        try:
            spisd = SoftSPI(-1, miso = Pin(13), mosi = Pin(26), sck = Pin(14))
            sd = SDCard(spisd, Pin(27))
            
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
            else:
                print(str(e))
                int_state  = led_state(state = 'no SD card')
                print(int_state)
                time.sleep(2)
        except KeyboardInterrupt:
            sys.exit()


def init_adc(rst=19,
            pwdn=21,
            drdy=23,
            start=18,
            sck=15,
            mosi=4,
            miso=5):
    """Initialise the TI ADS1115 (16-bit ADC)
    TODO: Generalise pin assignment. """
    ads = ads1261evm.ADC1261(rst=rst, pwdn=pwdn, start=start, sck=sck, mosi=mosi, miso=miso, drdy = drdy)
    
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
    if ads is None:
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
    111 (7): 'other' - Other error or state not set.
    
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
    i = 0
    while actualname in os.listdir(folder):
        i += 1
        actualname = "%s%d.%s" % (basename, i, ext)
    return actualname

def main():
    sd = init_sd()
    if sd is None: main()
    int_state = led_state(state = 'ok', pins = [15, 2, 4])
    pwm = init_pwm(pin = 33, freq = 1000, duty_cycle=512)
    
    adc = init_adc()
    adc.setup_measurements()
    adc.set_frequency(40000, 'sinc4')
    gain = 2 # can be adjusted
    adc.PGA(GAIN=gain) 
    adc.mode1(CHOP='normal', CONVRT='continuous', DELAY='50us')

    filename = unique_file(basename = 'data', ext = 'txt', folder = 'sd') # checks if this filename exists. If so, increment by 1 to prevent overwrite.
    filename = 'sd/' + filename
    
    log_file = 'log.txt' # Not used as yet. TODO: Implement logger output for debugging.

    # Initialise new datataking file.
    column_names = 'Time (s),AlGaN/GaN Sensor (mV),Temperature (mV)\n' # 'A2-A3 (mV)'
    init_write(column_names = column_names, filename = filename)

    # Start taking measurements.
    start_time = time.time() 
    last_measurement = utime.ticks_us()
    voltages0, voltages1 = [], []
    total_cycle_us = 1000 
    on_cycle_us = 500
    
    if on_cycle_us > total_cycle_us: on_cycle_us = total_cycle_us
    
    off_cycle_us = total_cycle_us - on_cycle_us

    while True: 
        if (time.time() - start_time) < 1:
            if (utime.ticks_us() - last_measurement) <= on_cycle_us:
                # if in the first half, collect gan measurement
                adc.start.on() # this repeats - how to set flag to ensure it doens't?
                adc.choose_inputs(positive='AIN2', negative='AIN3') # how to ensure this doesn't repeat?
                try:
                    voltage0 = adc.collect_measurement(method = 'hardware', gain = gain)
                    voltages0.append(voltage0)
                except Exception as e:
                    print(e)
                    sys.exit(1)

            elif ((utime.ticks_us() - last_measurement) <= total_cycle_us) and ((utime.ticks_us() - last_measurement) > on_cycle_us):
                # if in second half, collect temperature measurement
                adc.start.off()
                adc.choose_inputs(positive='AIN6', negative='AIN7')
                try:
                    voltage1 = adc.collect_measurement(method = 'hardware', gain = gain)
                    voltages1.append(voltage1)
                except Exception as e:
                    print(e)
                    sys.exit(1)

            elif (utime.ticks_us() - last_measurement) > total_cycle_us:
                # after the cycle, reset
                last_measurement = utime.ticks_us()
            
            else:
                # Hard to imagine how you'd get here.
                print("System error. Somehow outside the timed cycle bounds.")
                sys.exit(1)
        else:
            # calculate average
            time_since_start = str(time.time() - start_time)
            lenv0, lenv1 = len(voltages0), len(voltages1)
            
            if lenv0 <=1: lenv0 = 1 # just in case it fails to take a reading.
            if lenv1 <=1: lenv1 = 1
            
            average_voltages0 = str(sum(voltages0) / lenv0)
            average_voltages1 = str(sum(voltages1) / lenv1)
            
            print(average_voltages0, average_voltages1, lenv0, lenv1)

            voltages0, voltages1 = [], []
            
            # write to csv
            data = str(time_since_start + ',' + average_voltages0 + ',' + average_voltages1 + '\n')
            write(data = data, filename = filename)
            
            # restart
            start_time = time.time()


if __name__ == '__main__':
    """ To be implemented. Maybe in boot.py? """
    # main()
    pass