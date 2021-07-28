# esp32_datalogger

A datalogger based on the ESP32 (with WiFi and Bluetooth as standard). Built on micropython.

This uses a 24-bit ADC to accept reads and saves them to an SD card. Neither WiFi nor Bluetooth is implemented - but definitely doable.

To use:

#### Connect the wiring
The one with 30 GPIOs:
https://randomnerdtutorials.com/getting-started-with-esp32/

**SD Card:**
GND - GND
+3.3 - 3V3
+5 - Not connected
MOSI - D26
SCK - D14
CS - D27
MISO - D13
GND - GND

**ADS1115:**
VDD - 3V3
GND - GND
SCL - D5
SDA - D18
ADDR - Not connected.
ALRT - Not connected.
A0 - Sensor +
A1 - Sensor -
A2 - Not connected.
A3 - Not connected.

**Status LEDs:**
D15 - 100 Ohm - LED+ - GND (LED-)
D2 - 100 Ohm - LED+ - GND (LED-)
D4 - 100 Ohm - LED+ - GND (LED-)

**Software**
Download the repo

    git clone https://github.com/jeremygilly/esp32_datalogger

Start a new virtual environment

    python3 -m venv venv
    source venv/bin/activate

Download the required dependencies

    pip3 install -r requirements.txt

Continue...

## Possible Errors
**A fatal error occurred: Failed to connect to ESP32: Timed out waiting for packet header**
Hold down the boot/flash pin while running this from the command line. Further information is here: https://randomnerdtutorials.com/solved-failed-to-connect-to-esp32-timed-out-waiting-for-packet-header/

To download Espressif's codebase:
https://boneskull.com/micropython-on-esp32-part-1/

*Binaries:*
    https://micropython.org/download/esp32/

### Useful stuff:
    esptool.py --chip esp32 --port {Your USB location} --baud 115200 write_flash 0x1000 {Your saved binary location}

You may find -x 0x1000 required (but I have not found this to be reliable). You may also be required to press the BOOT/FLASH button during upload if it is struggling to connect.

#### Did it work? Open a screen

    screen {Your USB location} 115200
    help()

#### To exit (i.e. detach or kill a screen)

    ctrl+a 
    ctrl+d # to detach but you'd like to return
    ctrl+k # to kill it and reinitalise next time

#### USB location can be found with (connect/disconnect your USB device to confirm its name)

    ls /dev/tty.* 

#### Want to see an LED blink?
1. Go to the screen.
2. Type the following

        from machine import Pin
        led = Pin(2, Pin.OUT) # this is the default LED pin location on ESP-WROOM-32. YMMV.
        led.on()
        led.off()

3. Detach or kill session.

#### Ampy
It's already installed for you if you used the requirements.txt file above. Use

    ampy --help

For more information on how to use the program. For example, to install a new module that you got through git:

    ampy --port {Your USB Port name} --baud {Baud rate, mine is 115200} put {Path/to/file}

For example, to install the ADS1115 library:

    git clone https://github.com/robert-hh/ads1x15.git
    ampy --port {Your USB Port name} --baud {Baud rate, mine is 115200} put ads1x15/ads1x15.py

To use it:
    
    import ads1x15

#### SDCard - how to install
Find locally or download sdcard.py (https://github.com/micropython/micropython/tree/master/drivers/sdcard):

    ampy --port {Your USB Port name} --baud {Baud rate, mine is 115200} put {path/to/sdcard.py}

Then

    import sdcard

#### Need to navigate the SDcard filesystem?
    https://stackoverflow.com/questions/5137497/find-current-directory-and-files-directory