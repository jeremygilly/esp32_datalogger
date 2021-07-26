# esp32_datalogger

A datalogger based on the ESP32 (with WiFi and Bluetooth as standard). Built on micropython.

This uses a 24-bit ADC to accept reads and saves them to an SD card. Neither WiFi nor Bluetooth is implemented - but definitely doable.

To use:
Download the repo
    git clone https://github.com/jeremygilly/esp32_datalogger

Start a new virtual environment
    python3 -m venv venv

Download the required dependencies
    pip3 install -r requirements.txt

Continue...

## Possible Errors
**A fatal error occurred: Failed to connect to ESP32: Timed out waiting for packet header**
Hold down the boot/flash pin while running this from the command line. Further information is here: https://randomnerdtutorials.com/solved-failed-to-connect-to-esp32-timed-out-waiting-for-packet-header/

To download Espressif's codebase:
https://boneskull.com/micropython-on-esp32-part-1/

### Useful stuff:
    esptool.py --chip esp32 --port {Your USB location} --baud 115200 write_flash -x 0x1000 {Your saved binary location}

Did it work?
    screen {Your USB location} 115200
    help()

To exit (i.e. detach screen)
    ctrl+a ctrl+d

USB location can be found with (connect/disconnect your USB device to confirm its name)
    ls /dev/tty.* 

