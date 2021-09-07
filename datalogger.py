""" Main datalogger function 

In case you want to run this from the REPL:
import datalogger; import uasyncio as asyncio; loop = asyncio.get_event_loop();loop.run_forever(datalogger.main())

Start here:

import datalogger, ads1261evm, utime
from micropython import const
from machine import Pin, SPI
adc = ads1261evm.ADC1261()
print('set up measurements')
adc.reset()
adc.setup_measurements()
adc.set_frequency(19200, 'sinc4')
print("Frequency:", adc.check_frequency(print_freq = False))
gain = const(2) # can be adjusted
adc.PGA(GAIN=gain)
adc.PGA(GAIN=gain) 
print("Gain:", adc.check_PGA()[1])
adc.mode1(CHOP='normal', CONVRT='continuous', DELAY='0us')
print("Mode 1:", adc.check_mode1())
wri = adc.spi.write_readinto # bound method
inpmux1 = datalogger.input_bytes(adc, 'AIN3', 'AIN4')
inpmux2 = datalogger.input_bytes(adc, 'AIN6', 'AIN7')
i1, i2 = memoryview(inpmux1), memoryview(inpmux2)
convert = adc.convert_to_mV
reference = const(5000)
max_bits = const(2**23)
factor = reference/(max_bits * gain)
r, rdata = bytearray(5), bytes(b'\x12\x00\x00\x00\x00') # initalise a bytearray
rmv, wmv = memoryview(r), memoryview(rdata)
imv = memoryview(bytearray(5))
r1, r2 = bytearray(5), bytearray(5)
r1mv, r2mv = memoryview(r1), memoryview(r2)


Not yet implemented: WiFi removal of data.
"""

import os, gc, math
from machine import Pin, SoftSPI, PWM, SPI, freq
from sdcard import SDCard
import sys
import ads1261evm
import time
import utime
import uasyncio as asyncio
from micropython import const

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
        pwm.freq(freq)  # in Hz - really accurate as measured on oscilloscope!
        pwm.duty(duty_cycle)  # max = 1023 = 100%
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
            spisd = SoftSPI(miso=Pin(27), mosi=Pin(25), sck=Pin(26))
            sd = SDCard(spisd, Pin(33))
            
            vfs = os.VfsFat(sd)
            os.mount(vfs, '/sd')  # can't mount something that's already been mounted - will trigger EPERM error
            led_state(state='ok')
            print('Successfully mounted SD card.')
            return sd
        except OSError as e:
            print(e)
            if str(e) == 'no SD card':
                int_state  = led_state(state=str(e))
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
            sck=14,
            mosi=13,
            miso=12):
    """Initialise the TI ADS1115 (16-bit ADC)
    TODO: Generalise pin assignment. """
    ads = ads1261evm.ADC1261(rst=rst, pwdn=pwdn, start=start, sck=sck, mosi=mosi, miso=miso, drdy = drdy)
    # ads.spi = SPI(1,polarity=0,phase=1,baudrate=8000000,bits=8,firstbit=SPI.MSB,sck=Pin(sck),mosi=Pin(mosi),miso=Pin(miso))
    
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


def write(data, filename='data.txt'):
    """ Appends to a file that already exists.
    It also closes after each append to minimise dataloss during sudden removal. """
    try:
        with open(filename, 'a') as f:
            f.write(data)
        return 0
    except OSError as e:
        if str(e) == '[Errno 5] EIO':
            led_state(state='no sd card')
            time.sleep(1)
            main()
        elif str(e) == '[Errno 22] EINVAL':
            led_state(state='no sd card')

            main()

def led_state(state='other', pins=[15, 2, 4]):
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

@micropython.native
def convert_mV(rmv):
    if rmv[2] > 127:
        return -(2**24 - ((rmv[2] << 16) + (rmv[3] << 8) + rmv[4])) * 5000/(2*2**23)
    else:
        return ((rmv[2] << 16) + (rmv[3] << 8) + rmv[4])* 5000/(2*2**23)

@micropython.native
def get_measurement(_i, wri, wmv, rmv, imv):
    # wri(_i, imv)
    # wri(_i, imv)
    wri(wmv, rmv) # Old conversion data. Discard.
    wri(wmv, rmv) # New conversion data. Keep.
    # wri(wmv, rmv) # New conversion data. Keep.
    # wri(wmv, rmv) # New conversion data. Keep.
    # return (rmv[2] << 16) + (rmv[3] << 8) + rmv[4]
    return convert_mV(rmv)
    
def mV_temp(half, half_det, denom, br0rt, R):
    ''' convert the mv to RTD '''
    return half + math.sqrt(half_det + br0rt*R)/denom

def input_bytes(adc, positive, negative):
    ''' Takes an ADC object, positive terminal, and negative terminal.
    Returns a byte array with the corresponding register command for an ADS1261.
    '''
    register_data = int(adc.INPMUXregister[positive] << 4) + adc.INPMUXregister[negative]
    command = adc.commandByte1["WREG"][0] + adc.registerAddress["INPMUX"]
    return bytes([command, register_data, 0, 0, 0])

def measure(filename, adc = init_adc()):
    print('set up measurements')
    adc.reset()
    adc.setup_measurements()
    adc.set_frequency(19200, 'sinc4')
    print("Frequency:", adc.check_frequency(print_freq = False))
    gain = const(2) # can be adjusted but must update convert_mV
    adc.PGA(GAIN=gain)
    adc.PGA(GAIN=gain) 
    print("Gain:", adc.check_PGA()[1])
    # adc.mode1(CHOP='normal', CONVRT='continuous', DELAY='0us')
    adc.mode1()
    print("Mode 1:", adc.check_mode1())
    
    wri = adc.spi.write_readinto # bound method

    inpmux1 = input_bytes(adc, 'AIN3', 'AIN4')
    inpmux2 = input_bytes(adc, 'AIN6', 'AIN7')
    i1, i2 = memoryview(inpmux1), memoryview(inpmux2)

    # Start taking measurements.
    v0, v1 = 0,0
    total_cycle_us = 1000 
    on_cycle_us = 500
    
    if on_cycle_us > total_cycle_us: on_cycle_us = total_cycle_us
    
    global_start = time.time()
    start_time = time.time() 

    i = 0
    start = gc.mem_free()
    start_ticks = utime.ticks_ms()
    
    r1, r2 = bytearray(5), bytearray(5)
    r1mv, r2mv = memoryview(r1), memoryview(r2)
    rdata = bytes(b'\x12\x00\x00\x00\x00') # initalise a bytearray
    wmv = memoryview(rdata)
    imv = memoryview(bytearray(5))

    # Make the commands from the adc library local
    starton = adc.start.on
    startoff = adc.start.off
    drdy = adc.drdy
    convert = adc.convert_to_mV
    reference = const(5000)
    max_bits = const(2**23)
    factor = reference/(max_bits * gain)
    switch_current = Pin(22, Pin.OUT)
    fc = switch_current.on
    rc = switch_current.off

    desired_frequency = 1000  # Hz
    # delay = (1/desired_frequency*1e6 - 700)/2 # (seconds/period - average iteration time) / 2, 650 = 827/0.93 Hz
    delay = 165
    delay = int(delay)
    print(delay)
    flag = True
    wri(i1, imv) # 160 µs? Pass along to something else?

    # for the temperature calculation
    a, b, R0 = 3.9083e-3, -5.775e-7, 1000
    half, half_det, denom, br0rt = -a*R0/(2*b*R0), (a*R0)**2 - 4*b*R0**2, 2*b*R0, 4*b*R0
    t = mV_temp
    while True: 
        try:
            while (time.time() - start_time) < 0.93: # takes 60 ms to write to SD card
                # Average time per iteration: 601 µs
                # if in the first half, collect gan measurement
                fc() # forward current
                i += 1 # place here to reduce switch noise
                v0 += get_measurement(_i=i1, wri=wri, wmv=wmv, rmv=r1mv, imv=imv)
                wri(i2, imv) # 160 µs? Pass along to something else?
                utime.sleep_us(delay)
                
                rc() # reverse current
                # if in second half, collect temperature measurement
                v1 += get_measurement(_i=i2, wri=wri, wmv=wmv, rmv=r2mv, imv=imv)
                wri(i1, imv) # 160 µs? Pass along to something else?
                utime.sleep_us(delay)

            if flag:
                flag = False
                fc()
            else:
                flag = True
                rc()

            s = utime.ticks_us()
            time_since_start = str(time.time() - global_start)
            
            average_voltages0 = str(v0 / i) # removed factor
            temp = t(half, half_det, denom, br0rt, 10*v1/i) # 10 = mV/100e-6, change to 5 for 200 µA supply.
            average_voltages1 = str(temp) # removed factor
            
            print('\n', time_since_start, average_voltages0, average_voltages1, i, v0, v1)
            v0, v1, i = 0, 0, 0
            
            data = str(time_since_start + ',' + average_voltages0 + ',' + average_voltages1 + '\n')
            write(data = data, filename = filename)
            
            # restart
            start_time = time.time()
            print("Time to save (us):", utime.ticks_us() - s, '\n')

        except KeyboardInterrupt:
            adc.reset()
            sys.exit(1)

        except MemoryError as e:
            print("Cycles:", i)
            print("Used memory (bytes):", start - gc.mem_free())
            print("Time to full (us):", utime.ticks_ms() - start_ticks)
            led_state('adc')
            print(e)

        except Exception as e:
            led_state('adc')

def main():

    ''' 
    Thread 1: Change inputs, receive bytes from datalogger.
    Thread 2: Take bytes, convert to mV, calculate the average, store in sd card (in under a second?)
    Thread 3: FFT?
    '''
    freq(240000000) # up to 240 MHz
    sd = init_sd()
    if sd is None: main()
    int_state = led_state(state = 'ok', pins = [15, 2, 4])
    # pwm = init_pwm(pin = 33, freq = 1000, duty_cycle=512)
    
    # check if this filename exists. If so, increment by 1 to prevent overwrite.
    filename = unique_file(basename = 'data', ext = 'txt', folder = 'sd')  
    filename = 'sd/' + filename
    
    log_file = 'log.txt' # Not used as yet. TODO: Implement logger output for debugging.

    # Initialise new datataking file.
    column_names = 'Time (s),AlGaN/GaN Sensor (mV),Temperature (mV)\n' # 'A2-A3 (mV)'
    init_write(column_names = column_names, filename = filename)
    
    # create a global coroutine for data acquisition
    # create a global coroutine for averaging
    # create coroutine for writing to SD card
    measure(filename)
    
    

if __name__ == '__main__':
    """ To be implemented. Maybe in boot.py? """
    # main()
    pass