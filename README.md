# esp32_datalogger

A datalogger based on the ESP32 (with WiFi and Bluetooth as standard). Built on micropython.

This uses a 24-bit ADC to accept reads and saves them to an SD card. Neither WiFi nor Bluetooth is implemented - but definitely doable.

To use:
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

#### SDCard - how to install
Check micropython/drivers/sdcard:
upload sdcard.py (using ampy) then import sdcard

#### Need to navigate the SDcard filesystem?
    https://stackoverflow.com/questions/5137497/find-current-directory-and-files-directory