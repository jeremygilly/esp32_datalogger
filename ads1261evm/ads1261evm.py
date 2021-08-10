# ADS1261 Data Sheet: www.ti.com/lit/ds/symlink/ads1261.pdf
# ADS1261EVM User Guide: www.ti.com/lit/ug/sbau293a/sbau293a.pdf

# Testing:
# Keithley 2636B Source Measurement Unit: 1.225900 V
# ADS1261EVM: 1.248808 V
# Fluke 73III Multimeter: 1.266 V

import sys
import time
from machine import Pin, SoftSPI

class ADC1261:
    
    # From Table 29: Register Map Summary (pg 59 of ADS1261 datasheet)
    registerAddress = dict([
        ('ID', 0x0),    ('STATUS', 0x1),
        ('MODE0', 0x2), ('MODE1', 0x3),
        ('MODE2', 0x4), ('MODE3', 0x5),
        ('REF', 0x6),   ('OFCAL0', 0x7),
        ('OFCAL1', 0x8),('OFCAL2', 0x9),
        ('FSCAL0', 0xA),('FSCAL1', 0xB),
        ('FSCAL2', 0xC),('IMUX', 0xD),
        ('IMAG', 0xE),  ('RESERVED', 0xF),
        ('PGA', 0x10),  ('INPMUX', 0x11),
        ('INPBIAS', 0x12)
    ])
    
    # From Table 16: Command Byte Summary (pg 53) of ADS1261 data sheet.
    # Syntax: ('Mnemonic', [Byte 1, Description])
    # e.g. commandByte1['Mnemonic'][0] for Byte 1 value.
    commandByte1 = dict([
        ('NOP', [0x0, "No operation. Validates the CRC response byte sequence for errors."]),
        ('RESET', [0x6, "Reset all registers to default values."]),
        ('START', [0x8, "Start taking measurements."]),
        ('STOP', [0xA, "Stop taking measurements."]),
        ('RDATA', [0x12,"Read conversion data."]),
        ('SYOCAL', [0x16, "System offset calibration."]),
        ('GANCAL', [0x17, "Gain calibration."]),
        ('SFOCAL', [0x19, "Self offset calibration."]),
        ('RREG', [0x20, "Read register data. Did you add the register to read?"]),
        ('WREG', [0x40, "Write to register. Did you add the register to write to?"]),
        ('LOCK', [0xF2, "Lock registers from editing."]),
        ('UNLOCK', [0xF5, "Unlock registers from editing."])
    ])
    
    INPMUXregister = dict([
    # Check Table 43 in ADS1261 data sheet
        ('AINCOM', int('0000',2)),
        ('AIN0', int('0001',2)),
        ('AIN1', int('0010',2)),
        ('AIN2', int('0011',2)),
        ('AIN3', int('0100',2)),
        ('AIN4', int('0101',2)),
        ('AIN5', int('0110',2)),
        ('AIN6', int('0111',2)),
        ('AIN7', int('1000',2)),
        ('AIN8', int('1001',2)),
        ('AIN9', int('1010',2)),
        ('INTEMPSENSE', int('1011',2)), # Internal temperature sensor [positive or negative depending on field]
        ('INTAV4', int('1100',2)), # Internal (AVDD - AVSS)/4 [positive or negative depending on field]
        ('INTDV4', int('1101',2)), # Internal (DVDD/4) [positive or negative depending on field]
        ('ALLOPEN', int('1110',2)), # All inputs open
        ('VCOM', int('1111',2)) # Internal connection to V common
    ])
    
    OUTPMUXregister = dict([
        ('AIN0',int('0000',2)),
        ('AIN1',int('0001',2)),
        ('AIN2',int('0010',2)),
        ('AIN3',int('0011',2)),
        ('AIN4',int('0100',2)),
        ('AIN5',int('0101',2)),
        ('AIN6',int('0110',2)),
        ('AIN7',int('0111',2)),
        ('AIN8',int('1000',2)),
        ('AIN9',int('1001',2)),
        ('AINCOM',int('1010',2)),
        ('NONE',int('1111',2)),
    ])
    
    available_data_rates = dict([
        # Check Table 32 - ADS1261 data sheet. All values are floats in SPS.
        (float(2.5), int('00000',2)),
        (5, int('00001',2)),
        (10, int('00010',2)),
        (float(16.6), int('00011',2)),
        (20, int('00100',2)),
        (50, int('00101',2)),
        (60, int('00110',2)),
        (100, int('00111',2)),
        (400, int('01000',2)),
        (1200, int('01001',2)),
        (2400, int('01010',2)),
        (4800, int('01011',2)), 
        (7200, int('01100',2)), 
        (14400, int('01101',2)),
        (19200, int('01110',2)),
        (25600, int('01111',2)),
        (40000,int('10000',2))
    ])
        
    available_digital_filters = dict([
        # Check Table 32 - ADS1261 data sheet. sinc4 has the greatest noise attenuation and greatest time constant.
        ('sinc1', int('000',2)),
        ('sinc2', int('001',2)),
        ('sinc3', int('010',2)),
        ('sinc4', int('011',2)),
        ('fir', int('100',2)),
    ])
    
    available_gain = dict([
        (1, int('000',2)),
        (2, int('001',2)),
        (4, int('010',2)),
        (8, int('011',2)),
        (16, int('100',2)),
        (32, int('101',2)),
        (64, int('110',2)),
        (128, int('111',2))
    ])
    
    available_reference = dict([
        ('Internal Positive', int('00',2)<<2),
        ('AVDD', int('01',2)<<2),
        ('AIN0', int('10',2)<<2),
        ('AIN2', int('11',2)<<2),
        ('Internal Negative', int('00',2)),
        ('AVSS', int('01',2)),
        ('AIN1', int('10',2)),
        ('AIN3', int('11',2)),
    ])
    
    mode1register = dict({
        ('normal', int('00',2)<<5),
        ('chop', int('01',2)<<5),
        ('2-wire ac-excitation', int('10',2)<<5),
        ('4-wire ac-excitation', int('11',2)<<5),
        ('continuous', int('0',2)<<4),
        ('pulse', int('1',2)<<4),
        ('0us', int('0000',2)),
        ('50us', int('0001',2)),
        ('59us', int('0010',2)),
        ('67us', int('0011',2)),
        ('85us', int('0100',2)),
        ('119us', int('0101',2)),
        ('189us', int('0110',2)),
        ('328us', int('0111',2)),
        ('605us', int('1000',2)),
        ('1.16ms', int('1001',2)),
        ('2.27ms', int('1010',2)),
        ('4.49ms', int('1011',2)),
        ('8.93ms', int('1100',2)),
        ('17.8ms', int('1101',2))
    })
    
    # Constant current options:
    IMAG_register = dict({
        ('off', int('0000',2)),
        ('50', int('0001',2)),
        ('100', int('0010',2)),
        ('250', int('0011',2)),
        ('500', int('0100',2)),
        ('750', int('0101',2)),
        ('1000', int('0110',2)),
        ('1500', int('0111',2)),
        ('2000', int('1000',2)),
        ('2500', int('1001',2)),
        ('3000', int('1010',2)),
    })
    
    BOCSmagnitude_register = {
        'off':int('000',2),
        '50na':int('001',2),
        '200na':int('010',2),
        '1ua':int('011',2),
        '10ua':int('100',2)
    }
    
    inv_registerAddress = {v: k for k, v in registerAddress.items()}
    inv_INPMUXregister = {v: k for k, v in INPMUXregister.items()}
    inv_available_data_rates = {v: k for k, v in available_data_rates.items()}
    inv_available_digital_filters = {v: k for k, v in available_digital_filters.items()}
    inv_available_gain = {v: k for k, v in available_gain.items()}
    inv_available_reference = {v: k for k, v in available_reference.items()}
    inv_mode1register = {v: k for k, v in mode1register.items()}
    inv_IMAG_register = {v: k for k, v in IMAG_register.items()}
    inv_OUTPMUXregister = {v: k for k, v in OUTPMUXregister.items()}
    inv_BOCSmagnitude_register = {v: k for k, v in BOCSmagnitude_register.items()}
    
    def __init__(self, 
                    bus = 0, 
                    device = 0, 
                    speed = 16000000, 
                    rst = 19, 
                    pwdn = 21, 
                    drdy = 16,
                    start = 18,
                    sck = 15,
                    mosi = 4,
                    miso = 5):
        
        # ESP32 using Micropython
        # DIN = SPI MOSI, D4
        # DOUT = SPI MISO, D5
        # SCLK = SPI SCLK, D15
        # /CS = SPI CE0_N, ???
        
        self.rst = Pin(rst, Pin.OUT)
        self.pwdn = Pin(pwdn, Pin.OUT)
        self.drdy = Pin(drdy, Pin.OUT)
        self.start = Pin(start, Pin.OUT)

        # 9.5.1 of ADS1261 datasheet (pg 50): CPOL = 0, CPHA = 1
        # MSB first: Table 12. Be wary of full-scale and offset calibration registers (need 24-bit for words)

        self.spi = SoftSPI(polarity = 0, phase = 1, sck = Pin(sck), mosi = Pin(mosi), miso = Pin(miso), firstbit=SoftSPI.MSB)

        self.bits = 24 # This is to do with future conversions (1/2**24) - not an SPI read/write issue.
        
        self.arbitrary = 0x10 # This is command byte 2 as per Table 16.
        self.CRC2 = 1 # Change this to 0 to tell the register if Cyclic Redundancy Checks are disabled (and 1 to enable) per Table 35: MODE3 Register Field Description.
        self.zero = 0 # This is command byte 4 per Table 16.
    
    def send(self, hex_message, human_message="None provided"):
        try:
            byte_message = [int(list_element,2) if type(list_element) != int else list_element for list_element in hex_message]
            wbuf = bytes(byte_message)
            rbuf = bytearray(len(wbuf))
            self.spi.write_readinto(wbuf, rbuf)
            return rbuf
        except Exception as e:
            print('Send failed.')
            print(wbuf, rbuf)
            print ("Attempted byte message:", wbuf)
            print(e)
             
            
                
    def read_register(self, register_location, CRC = 'off'):
        ''' Takes the register location. Requires CRC to be None or any other value.
        If the CRC bit is unknown, function will assume it is off, then on.
        Returns the value in the read register.'''
        register_location = register_location.upper()
        hex_message = [self.commandByte1['RREG'][0]+self.registerAddress[register_location], self.arbitrary]
        if CRC == None:
            read_message = hex_message + [199] + [self.zero]*8
            returnedMessage = self.send(hex_message=read_message)
            if returnedMessage[1] != int(hex_message[0],2):
                print("Failed readback. CRC may be on.")
            else:
                return returnedMessage[4]
        elif CRC.lower() == 'off':
            read_message = hex_message + [self.zero]*1
            #~ print("read message if CRC is off:", read_message)
            #~ print("CRC:", self.crc(hex_message), int(self.crc(hex_message),2))
            returnedMessage = self.send(hex_message=read_message)
            return returnedMessage[2]
            #~ print("Returned message:", returnedMessage)
        elif CRC.lower() == 'on':
            pass
            
    
            #~ if :
                #~ return returnedMessage[2]
            #~ else:
                #~ return -1           
            
    def write_register(self, register_location, register_data):
        # expects to see register_location as a human readable string
        register_location = register_location.upper()
        # expects to see register_data as a binary string
        if not isinstance(register_data, str):
            register_data = format(register_data,'08b')
        
        hex_message = [self.commandByte1['WREG'][0]+self.registerAddress[register_location],int(register_data,2),0,0,0]
        #~ read_message = hex_message + [self.crc(hex_message)] + [self.zero]*1
        read_message = hex_message
        #~ print("WREG hex and read messages:", hex_message, read_message)
        write_check = self.send(read_message)
        #~ print("Write_check:", write_check)

        #~ if write_check[-1] != crc_2:
            #~ print("CRC output error. Sent:", crc_2, "Recevied:", write_check[-1])
            #~  

        if write_check[1] == read_message[0]:
            read = self.read_register(register_location)
            if read == -1:
                print("Read back failed. Requires write_register review.")
                print(read, hex_message)
            elif read == int(register_data,2):
                #~ print("Register written successfully.")
                #~ print("Read register location:", register_location, "Read data:", format(read,'08b'))
                pass
            elif register_location.upper() == 'STATUS':
                pass
            else:
                print("Unexplained fail regarding writing to a register. Read back was unexpected.")
                print("Register Location:", register_location, "- Read back:", read, "- Written/sent back:", write_check, "- Data sent:", int(register_data,2))
#                 
                pass
        else:
            print("Error writing register - failed WREG command")
            print("DIN [0]:", hex_message, "- DOUT [1]:", write_check)
            print("Have you enabled setup_measurements() before running this WREG command?")
             

    def choose_inputs(self, positive, negative = 'VCOM'):
        input_pins = int(self.INPMUXregister[positive]<<4)+self.INPMUXregister[negative]
        self.write_register('INPMUX', format(input_pins,'08b'))
#        self.check_inputs()
    
    def check_inputs(self):
        read = self.read_register('INPMUX')
        print("Input polarity check --- Positive side:", self.inv_INPMUXregister[int(format(read,'08b')[:4],2)], "- Negative side:", self.inv_INPMUXregister[int(format(read,'08b')[4:],2)])
    
    def set_frequency(self, data_rate = 20, digital_filter = 'FIR', print_freq=True):
        data_rate = float(data_rate) # just to ensure we remove any other data types (e.g. strings)
        digital_filter = digital_filter.lower() # to ensure dictionary matching
        rate_filter = int(self.available_data_rates[data_rate]<<3)+int(self.available_digital_filters[digital_filter])
        self.write_register('MODE0', format(rate_filter,'08b'))
        self.check_frequency(print_freq=print_freq)
        
    def check_frequency(self, print_freq=True):
        read = self.read_register('MODE0')
        data_rate = self.inv_available_data_rates[int(format(read,'08b')[:5],2)]
        digital_filter = self.inv_available_digital_filters[int(format(read,'08b')[5:],2)]
        if (print_freq==True): 
            print("Data rate and digital filter --- Data rate:", data_rate, 
            "SPS - Digital Filter:", digital_filter)
        return data_rate, digital_filter
        
    def check_ID(self):
        ''' Checks the version of the ADC that you have.
            Returns the DeviceID (ADS1261x) and the Revision ID (0001, etc). '''
        hex_checkID = [self.commandByte1['RREG'][0]+self.registerAddress['ID'],
                        self.arbitrary, 
                        self.zero]
        # 0x20 + 0x0 + 0x0 + 0x0
        ID = self.send(hex_checkID)
        #~ print("Sent:", hex_checkID, "Received:", ID) # for diagnostics only.
        if ID[1] == hex_checkID[0]:
            ID = bin(ID[2])
            ID_description = {"1000":"ADS1261 or ADS1261B", "1010":"ADS1260B"} # Table 30 from ADS1261 data sheet
            #~ print("Device ID:", ID_description[ID[2:6]], "- Revision ID:", ID[6:10])
            [DeviceID, RevisionID] = ID_description[ID[2:6]], ID[6:10]
            return DeviceID, RevisionID
        else:
            print ("Failed to echo byte 1 during ID check")
            print ("Register sent:", ID[1], "\nRegister received:", hex_checkID[1])
             
            
    def clear_status(self, CRCERR = 0, RESET = 0):
        send_status = 0
        CRCERR = CRCERR<<6
        send_status = send_status + CRCERR + RESET
        self.write_register('STATUS', format(send_status,'08b'))
        self.check_status()
        
    def check_status(self):
        read = self.read_register('STATUS')
        byte_string = list(map(int,format(read,'08b')))
        LOCK_status = 0 if byte_string[0] == 0 else 1
        CRCERR_status = 0 if byte_string[1] == 0 else 1
        PGAL_ALM_status = 0 if byte_string[2] == 0 else 1
        PGAH_ALM_status = 0 if byte_string[3] == 0 else 1
        REFL_ALM_status = 0 if byte_string[4] == 0 else 1
        DRDY_status = 0 if byte_string[5] == 0 else 1
        CLOCK_status = 0 if byte_string[6] == 0 else 1
        RESET_status = 0 if byte_string[7] == 0 else 1
        return LOCK_status, CRCERR_status, PGAL_ALM_status, PGAH_ALM_status, REFL_ALM_status, DRDY_status, CLOCK_status, RESET_status
        
    def print_status(self):
        LOCK_status, CRCERR_status, PGAL_ALM_status, PGAH_ALM_status, REFL_ALM_status, DRDY_status, CLOCK_status, RESET_status = self.check_status()
        LOCK_status = "Unlocked" if LOCK_status == 0 else "Locked"
        CRCERR_status = "No CRC error." if CRCERR_status == 0 else "CRC Error"
        PGAL_ALM_status = "No alarm" if PGAL_ALM_status == 0 else "Alarm"
        PGAH_ALM_status = "No alarm" if PGAH_ALM_status == 0 else "Alarm"
        REFL_ALM_status = "No alarm" if REFL_ALM_status == 0 else "Alarm"
        DRDY_status = "Not new" if DRDY_status == 0 else "New"
        CLOCK_status = "Internal" if CLOCK_status == 0 else "External"
        RESET_status = "No reset" if RESET_status == 0 else "Reset"
        print("\n *** Status Register Check: ***"
                "\nRegister lock status:", LOCK_status, 
                "\nCRC Error:", CRCERR_status,
                "\nPGA Low Alarm:", PGAL_ALM_status,
                "\nPGA High Alarm:", PGAH_ALM_status,
                "\nReference Low Alarm:", REFL_ALM_status,
                "\nData ready:", DRDY_status,
                "\nClock:", CLOCK_status,
                "\nReset:", RESET_status)
    
    def crc(self, input_bitstring, check_value = None, polynomial_bitstring = '100000111'):
        ''' Calculates the CRC remainder of a string of bits using a chosen polynomial.
        If check_value is not used, it returns the crc remainder. 
        If it is used, the function returns whether the check_value is true. '''
        
        # Check data format (change from int to string if necessary)
        for element in range(len(input_bitstring)):
            if type(input_bitstring[element]) == int:
                input_bitstring[element] = format(input_bitstring[element], '08b')
            if input_bitstring[element][:2] =='0b':
                input_bitstring[element] = input_bitstring[element][2:]
        '''# Check input length. If only one byte or 8 bits, add arbitrary byte.
        if len(input_bitstring) == 1 or len(input_bitstring) == 8:
            input_bitstring += '0'*8
        print("Step 2 of CRC:", input_bitstring)'''
        # Join into single bit string
        input_bitstring = ''.join(input_bitstring)
        # Check that our bit string is actually a string of 0s and 1s
        if (input_bitstring[0] != '0' and input_bitstring[0] != '1'):
            print("Error with CRC remainder bitstring. This doesn't seem like a bitstring")
            print("You sent:", input_bitstring)
            sys.exit()

        # Throw warning for incorrect polynomial divisor
        if polynomial_bitstring != '100000111':
            print("Warning: polynomial for CRC division does not match TI ADS1261 datasheet (pg 52).")
            print("Continuing...")

        polynomial_bitstring = polynomial_bitstring.lstrip('0')
        len_input = len(input_bitstring)
        
        if check_value is None:
            # add initial padding for division
            initial_padding = '0' * (len(polynomial_bitstring) - 1)
        else:
            # check the value
            initial_padding = check_value
        
        input_padded_array = list(input_bitstring + initial_padding)
        
        while '1' in input_padded_array[:len_input]:
            cur_shift = input_padded_array.index('1')
            for i in range(len(polynomial_bitstring)):
                input_padded_array[cur_shift + i] = str(int(polynomial_bitstring[i] != input_padded_array[cur_shift + i]))
        
        if check_value is None:
            return ''.join(input_padded_array)[len_input:]
        else:
            return ('1' not in ''.join(input_padded_array)[len_input:])
 
    def mode1(self, CHOP = 'normal', CONVRT = 'continuous', DELAY = '50us'):
        # CHOP = 'normal', 'chop', '2-wire ac-excitation', or '4-wire ac-excitation'
        # CONVRT = 'continuous' or 'pulse'
        # DELAY = '0us', '50us', '59us', '67us', '85us', '119us','189us', '328us','605us','1.16ms','2.27ms','4.49ms','8.93ms', or '17.8ms'
        [CHOP, CONVRT, DELAY] = [CHOP.lower(), CONVRT.lower(), DELAY.lower()] # formatting
        send_mode1 = self.mode1register[CHOP]+self.mode1register[CONVRT]+self.mode1register[DELAY]
        send_mode1 = format(send_mode1, '08b')
        self.write_register('MODE1', send_mode1)
        self.check_mode1()
        
    def check_mode1(self):
        read = self.read_register('MODE1')
        byte_string = list(map(int,format(read,'08b')))#; print(byte_string)
        chop_bits = int(''.join(map(str,byte_string[1:3])),2)<<5
        convrt_bits = int(str(byte_string[3]),2)<<4
        CHOP = 'normal' if chop_bits == 0 else self.inv_mode1register[chop_bits]
        CONVRT = 'continuous' if convrt_bits == 0 else self.inv_mode1register[int(str(byte_string[3]),2)<<4]
        DELAY = self.inv_mode1register[int(''.join(map(str,byte_string[4:])),2)]
        return CHOP, CONVRT, DELAY
    
    def print_mode1(self):
        CHOP, CONVRT, DELAY = self.check_mode1()
        print("\n *** MODE 1 Register Check: ***"
                "\nChop and AC-Excitation Mode:", CHOP,
                "\nADC Conversion Mode:", CONVRT,
                "\nConversion Start Delay:", DELAY)

    def mode2(self,
            gpio3_connection = 'disconnect',
            gpio2_connection = 'disconnect',
            gpio1_connection = 'disconnect',
            gpio0_connection = 'disconnect',
            gpio3_direction = 'output',
            gpio2_direction = 'output',
            gpio1_direction = 'output',
            gpio0_direction = 'output'):
        a = [gpio3_connection, gpio2_connection, gpio1_connection, gpio0_connection, gpio3_direction, gpio2_direction, gpio1_direction, gpio0_direction]
        a = list(map(str.lower,a))
        b = []
        for item in a[:4]:
            if item =='disconnect':
                b.append(0)
            elif item =='connect':
                b.append(1)
            else:
                return "Connection must be 'disconnect' (default) or 'connect' only."
                
        for item in a[4:]:
            if item =='output':
                b.append(0)
            elif item =='input':
                b.append(1)
            else:
                return "Direction must be 'output' (default) or 'input' only."
      
        shifts = list(range(7,-1,-1))
        b = list(zip(b, shifts))
        b = [i[0] << i[1] for i in b]
        send_mode2 = sum(b)
        send_mode2 = format(send_mode2, '08b')
        self.write_register('MODE2', send_mode2)
        self.check_mode2()
        
    def check_mode2(self):
        read = self.read_register('MODE2')
        byte_string = list(map(int,format(read,'08b')))
        connections = ['disconnect' if i == 0 else 'connect' for i in byte_string [:4]]
        directions = ['output' if i == 0 else 'input' for i in byte_string [4:]]
        [gpio3_connection, gpio2_connection, gpio1_connection, gpio0_connection, gpio3_direction, gpio2_direction, gpio1_direction, gpio0_direction] = connections + directions
        return gpio3_connection, gpio2_connection, gpio1_connection, gpio0_connection, gpio3_direction, gpio2_direction, gpio1_direction, gpio0_direction
    
    def print_mode2(self):
        gpio3_connection, gpio2_connection, gpio1_connection, gpio0_connection, gpio3_direction, gpio2_direction, gpio1_direction, gpio0_direction = self.check_mode2()
        print("\n *** MODE 2 Register Check: ***"
                "\nGPIO3 Pin Connection to AIN5:", gpio3_connection,
                "\nGPIO2 Pin Connection to AIN4:", gpio2_connection,
                "\nGPIO1 Pin Connection to AIN3:", gpio1_connection,
                "\nGPIO0 Pin Connection to AIN2:", gpio0_connection,
                "\nGPIO3 Pin Direction:", gpio3_direction,
                "\nGPIO2 Pin Direction:", gpio2_direction,
                "\nGPIO1 Pin Direction:", gpio1_direction,
                "\nGPIO0 Pin Direction:", gpio0_direction)

    
    def mode3(self, 
                PWDN = 0,
                STATENB = 0,
                CRCENB = 0,
                SPITIM = 0,
                GPIO3 = 0,
                GPIO2 = 0,
                GPIO1 = 0,
                GPIO0 = 0):
        send_mode3 = [PWDN, STATENB, CRCENB, SPITIM, GPIO3, GPIO2, GPIO1, GPIO0]
        send_mode3 = ''.join(map(str,send_mode3))
        self.write_register('MODE3', send_mode3)
        self.check_mode3()
        
    def check_mode3(self):
        read = self.read_register('MODE3')
        #~ if len(read) > 1:
            #~ Note: this assumes CRC is off
            #~ read = read[2]
        try:
            byte_string = list(map(int,format(read,'08b')))
            PWDN_status = 0 if byte_string[0] == 0 else 1
            STATENB_status = 0 if byte_string[1] == 0 else 1
            CRCENB_status = 0 if byte_string[2] == 0 else 1
            SPITIM_status = 0 if byte_string[3] == 0 else 1
            GPIO3_status = 0 if byte_string[4] == 0 else 1
            GPIO2_status = 0 if byte_string[5] == 0 else 1
            GPIO1_status = 0 if byte_string[6] == 0 else 1
            GPIO0_status = 0 if byte_string[7] == 0 else 1
            return PWDN_status, STATENB_status, CRCENB_status, SPITIM_status, GPIO3_status, GPIO2_status, GPIO1_status, GPIO0_status
        except Exception as e:
            print(e)
            print(type(read), read)
             
    
    def print_mode3(self):
        PWDN_status, STATENB_status, CRCENB_status, SPITIM_status, GPIO3_status, GPIO2_status, GPIO1_status, GPIO0_status = self.check_mode3()
        PWDN_status = "Normal" if PWDN_status == 0 else "Software Power-Down Mode"
        STATENB_status = "No Status byte" if STATENB_status == 0 else "Status byte enabled"
        CRCENB_status = "No CRC" if CRCENB_status == 0 else "CRC enabled"
        SPITIM_status = "SPI auto-reset disabled" if SPITIM_status == 0 else "SPI auto-reset enabled"
        GPIO3_status = "Low" if GPIO3_status == 0 else "High"
        GPIO2_status = "Low" if GPIO2_status == 0 else "High"
        GPIO1_status = "Low" if GPIO1_status == 0 else "High"
        GPIO0_status = "Low" if GPIO0_status == 0 else "High"
        print("\n *** Mode 3 Register Check:*** "
                "\nSoftware Power-down mode:", PWDN_status,
                "\nSTATUS byte:", STATENB_status,
                "\nCRC Data Verification:", CRCENB_status,
                "\nSPI Auto-Reset Function:", SPITIM_status,
                "\nGPIO3 Data:", GPIO3_status,
                "\nGPIO2 Data:", GPIO2_status,
                "\nGPIO1 Data:", GPIO1_status,
                "\nGPIO0 Data:", GPIO0_status)
                
    def PGA(self, BYPASS = 0, GAIN = 1):
        # BYPASS can be 0 (PGA mode (default)) or 1 (PGA  bypass).
        send_PGA = int(BYPASS<<7)+int(self.available_gain[GAIN])
        send_PGA = format(send_PGA, '08b')
        self.write_register('PGA', send_PGA)
        self.check_PGA()
        
    def check_PGA(self):
        read = self.read_register('PGA')
        byte_string = list(map(int,format(read,'08b')))
        BYPASS_status = 0 if byte_string[0] == 0 else 1
        gain = self.inv_available_gain[int(''.join(map(str,byte_string[5:])),2)]
        return BYPASS_status, gain
    
    def print_PGA(self):
        BYPASS_status, gain = self.check_PGA()
        BYPASS_status = "PGA mode" if BYPASS_status == 0 else "PGA Bypass"
        print("\n *** PGA Register Check: ***"
                "\nPGA Bypass Mode:", BYPASS_status,
                "\nGain:", gain)

    def reference_config(self, reference_enable = 0, RMUXP = 'AVDD', RMUXN = 'AVSS'):
        # Note: Bit shifting not required when referencing dictionary (already happens at the dictionary level).
        # reference_enable must be 0 (disabled) or 1 (enabled)
        # RMUXP is the reference positive side, can be "Internal Positive", "AVDD", "AIN0", or "AIN2"
        # RMUXN is the reference negative side, can be "Internal Negative", "AVSS", "AIN1", or "AIN3"
        send_ref_config = int(reference_enable<<4) + self.available_reference[RMUXP] + self.available_reference[RMUXN]
        send_ref_config = format(send_ref_config, '08b')
        self.write_register('REF', send_ref_config)
        self.check_reference_config()
        
    def check_reference_config(self):
        read = self.read_register('REF')
        byte_string = list(map(int,format(read,'08b')))
        ref_enable_status = 0 if byte_string[3] == 0 else 1
        RMUXP_status = self.inv_available_reference[int(''.join(map(str,byte_string[4:6])),2)<<2]
        RMUXN_status = self.inv_available_reference[int(''.join(map(str,byte_string[6:])),2)]
        return ref_enable_status, RMUXP_status, RMUXN_status
    
    def print_reference_config(self):
        ref_enable_status, RMUXP_status, RMUXN_status = self.check_reference_config()
        ref_enable_status = "Disabled" if ref_enable_status == 0 else "Enabled"
        print("\n *** Reference Configuration Check: ***"
                "\nInternal Reference Enable:", ref_enable_status,
                "\nReference Positive Input:", RMUXP_status,
                "\nReference Negative Input:", RMUXN_status, "\n")
                
    def calibration(self, calibration = "SFOCAL"):
        # User offset calibration not implemented.
        calibration = [self.commandByte1[calibration][0], self.arbitrary, self.zero]
        self.send(calibration)
        
    def setup_measurements(self):
        #~ Based on Figure 101 in ADS1261 data sheet
        #~ Set reset and PWDN pins high
        self.rst.on()
        self.pwdn.on()
        self.start.on()
        
    def reset(self):
        self.rst.off()
        time.sleep(0.1)
        self.rst.on()
        return 0
    
    def syocal(self):
        # configure the ADC (done elsewhere)
        # Apply the calibration signal(i.e. connect/short the inputs)
        print("Please ensure inputs are shorted together")
        # Take the start pin high
        self.start1()
        # Before conversion completion, send the calibration command. Keep CS low
        syocal_message = [self.commandByte1['SYOCAL'][0], self.arbitrary]
        # delay for calibration time (Table 14, pg 49, ADS1261 data sheet
        self.send(syocal_message)
        return 0
    
    def sfocal(self):
        self.start1()
        sfocal_message = [self.commandByte1['SFOCAL'][0], self.arbitrary]
        self.send(sfocal_message)
        return 0
    
    def no_operation(self):
        nop_message = [self.commandByte1['NOP'][0], self.arbitrary]
        for item in nop_message:
            print(type(item), item)        
        print(self.send(nop_message))
        return 0
    
    def stop(self):
        stop_message = [self.commandByte1['STOP'][0], self.arbitrary, self.zero]
        self.send(stop_message)
        return 0
        
    def start1(self):
        start_message = [self.commandByte1['START'][0], self.arbitrary, self.zero]
        self.send(start_message)
        return 0
        
    def status_byte_trial(self):
        self.stop()
        self.reset()
        self.mode2(gpio3_connection = 'connect',
            gpio2_connection = 'connect',
            gpio1_connection = 'disconnect',
            gpio0_connection = 'disconnect',
            gpio3_direction = 'output',
            gpio2_direction = 'output',
            gpio1_direction = 'output',
            gpio0_direction = 'output')
        self.mode3(PWDN = 0,
                STATENB = 1,
                CRCENB = 0,
                SPITIM = 0,
                GPIO3 = 0,
                GPIO2 = 1,
                GPIO1 = 0,
                GPIO0 = 0)
        self.choose_inputs(positive = 'AIN2', negative = 'AIN3')
        self.start1()
        return self.collect_measurement(method = 'hardware', reference = 5000, gain = 1, status = 'enabled')
        
    def calculate_reference(self, no_samples = 20):
        self.setup_measurements()
        all_samples = []
        analog_supply = self.power_readback(); 
        self.reference_config(reference_enable = 1)
        self.mode1(); self.mode2(); self.mode3()

        self.mode2(gpio2_direction = 'output', gpio3_direction = 'output',
                   gpio2_connection = 'connect', gpio3_connection = 'connect')
        self.mode3(PWDN = 0,
            STATENB = 0,
            CRCENB = 0,
            SPITIM = 0,
            GPIO3 = 0,
            GPIO2 = 1,
            GPIO1 = 0,
            GPIO0 = 0)
        self.choose_inputs(positive = 'AIN0', negative = 'AIN1')
        self.PGA()
        self.start1()
        while(len(all_samples) < no_samples):
           all_samples.append(self.collect_measurement(method = 'hardware', 
                                reference = analog_supply, gain = 1))
        reference = sum(all_samples) / len(all_samples)
        return reference
        
    def ac_simple(self, measurement_type = 'DC'):
        ''' Frequency removed for easier change in other areas of future code. '''
        
        #~ print("AVDD to AVSS (mV):", self.power_readback())
        #~ print("AIN0 to AIN1 (mV):", external_reference)
        self.setup_measurements()
        # self.stop()
        # Reset device
        # self.reset()
        # self.set_frequency(data_rate = 14400, digital_filter = 'sinc1', print_freq = False)
        external_reference = self.calculate_reference()
        # self.stop()
        # self.reset()
        # clear status register
        #~ self.clear_status()
        
        # WREG 2.5 SPS, sinc4
        #~ self.set_frequency(data_rate = 1200, digital_filter = 'sinc4', print_freq = False)
        
        if measurement_type == 'AC':
            # WREG 4-wire ac-excitation (toggle on)
            self.mode1(CHOP = '4-wire ac-excitation', CONVRT = 'continuous', DELAY = '50us')
            # WREG select AIN 0 & 1 as external references (toggle on)
            self.mode3(PWDN = 0,
                STATENB = 1,
                CRCENB = 0,
                SPITIM = 0,
                GPIO3 = 0,
                GPIO2 = 0,
                GPIO1 = 0,
                GPIO0 = 0)
            self.reference_config(reference_enable = 0, RMUXP = 'AIN0', RMUXN = 'AIN1')
            reference = external_reference
            
        elif measurement_type == 'DC':
            reference = self.power_readback()
            # WREG 4-wire ac-excitation (toggle off)
            self.mode1(CHOP = 'normal', CONVRT = 'continuous', DELAY = '50us')
            # WREG hold GPIO 2 high (for +5 V)
            self.mode3(PWDN = 0,
                STATENB = 1,
                CRCENB = 0,
                SPITIM = 0,
                GPIO3 = 0,
                GPIO2 = 1,
                GPIO1 = 0,
                GPIO0 = 0)
            # WREG select AIN 0 & 1 as external references (toggle off)         
            self.reference_config(reference_enable = 1, RMUXP = 'AVDD', RMUXN = 'AVSS')
            
        else:
            print('The measurement_type was not "AC" or "DC"')
        
        # WREG connect GPIOs 2 & 3 (AIN 4 & 5)
        self.mode2(gpio3_connection = 'connect',
            gpio2_connection = 'connect',
            gpio1_connection = 'disconnect',
            gpio0_connection = 'disconnect',
            gpio3_direction = 'output',
            gpio2_direction = 'output',
            gpio1_direction = 'output',
            gpio0_direction = 'output')
        
        # self.mode3() # - set registers to default
        print('')
        return external_reference
        
    def test_gain(self):
        gains = [1,2,4,8,16,32,64,128]
        for gain in gains:
            self.clear_status()
            self.ac_test_all(gain = gain)
            self.print_status()

    def median(l):
        if len(l) % 2 == 0:
                return (l[int(len(l)/2-1)] + l[int(len(l)/2)]) / 2
        else:
                return l[int(len(l)/2)]

    def ac_test_all(self, gain):
        external_reference = self.ac_simple('AC')
        self.PGA(BYPASS = 0, GAIN = gain)
        self.print_PGA()
        # set all potential pairs
        terminals = ['AIN2', 'AIN3', 'AIN6', 'AIN7', 'AIN8', 'AIN9']
        #~ print("Number of terminals:", len(terminals))
        for j in range(len(terminals)-1):
            self.stop()
            self.choose_inputs(positive = terminals[j], negative = terminals[j+1])
            self.start1()
            samples = []
            for i in range(1,10):
                samples.append(self.collect_measurement(method='hardware', 
                reference=external_reference, gain = gain))
            
            print("Positive:", terminals[j], "Negative:", terminals[j+1], "-", self.median(samples), "mV")
        return 0
    
    def status(self, status_byte):
        PWDN_status, STATENB_status, CRCENB_status, SPITIM_status, GPIO3_status, GPIO2_status, GPIO1_status, GPIO0_status = status_byte
        return 0
        
    def maximum_gain(self, positive_input = 'AIN2', negative_input = 'AIN3', positive_reference = 'AIN0', negative_reference = 'AIN1', excitation_source = 'internal'):
        ''' Calculates the maximum gain between a pair of inputs.
            Intended for use with external references where the external reference
            or the inputs are likely to be clipped. '''
        self.setup_measurements()
        self.stop()
        self.reset()
        #~ self.set_frequency(data_rate = 1200, digital_filter = 'sinc2')
        external_reference = self.calculate_reference()
        #~ print("External reference (mV):", external_reference) # for diagnostics only.
        
        if excitation_source == 'internal':
            self.mode2(gpio3_connection = 'connect',
                gpio2_connection = 'connect',
                gpio1_connection = 'disconnect',
                gpio0_connection = 'disconnect',
                gpio3_direction = 'output',
                gpio2_direction = 'output',
                gpio1_direction = 'output',
                gpio0_direction = 'output')
            
            self.mode3(STATENB = 1,
                    GPIO3 = 0,
                    GPIO2 = 1)
        
        PWDN_status, STATENB_status, CRCENB_status, SPITIM_status, GPIO3_status, GPIO2_status, GPIO1_status, GPIO0_status = self.check_mode3()
        if STATENB_status == "No Status byte":
            self.mode3(PWDN = PWDN_status,
                    STATENB = 1,
                    CRCENB = CRCENB_status,
                    SPITIM = SPITIM_status,
                    GPIO3 = GPIO3_status,
                    GPIO2 = GPIO2_status,
                    GPIO1 = GPIO1_status,
                    GPIO0 = GPIO0_status)
                    
        status_byte = "enabled"
        # set external reference
        self.reference_config(RMUXP = positive_reference, RMUXN = negative_reference)
        self.choose_inputs(positive = positive_input, negative = negative_input)
        # try gain of 1 - 128, stop when there is a PGA alarm
        gains = [1,2,4,8,16,32,64,128]
        for previous_gain, gain in zip(gains, gains[1:]):
            self.stop()
            self.PGA(BYPASS = 0, GAIN = gain)
            #~ self.print_PGA()
            self.start1()
            result = self.collect_measurement(method = 'hardware', reference = external_reference, gain = gain, status = 'enabled')
            #~ print("Raw result:", result)
            if type(result) != float:
                return previous_gain
        return gains[-1]
    

    def collect_measurement(self, method='software', reference=5000, gain = 1, status = 'disabled', crc = 'disabled', bits = False):
        #~ Choose to use hardware or software polling (pg 51 & 79 of ADS1261 datasheet) 
        #~ Based on Figure 101 in ADS1261 data sheet
        i = 0
        rdata = [self.commandByte1['RDATA'][0],0,0,0,0,0,0,0,0]
        self.start1() # remove this if necessary.
        if method.lower() == 'hardware':
            response = -1
            while response == -1:
                if i > 1000: print("Have you run start1()?");  
                try:
                    if self.drdy.value(): rdata_status = True # set flag to show measurements were taking place
                    if not self.drdy.value() and rdata_status == True: # must have been previously getting conversions and is now low
                        rdata_status = False # show we've just read it. Prevents old conversions coming through - maybe?
                        read = self.send(rdata)
                        #~ print(read) # remember to remove this!
                        if status != 'disabled' and crc == 'disabled':
                            #~ print("Status enabled, CRC-2 disabled")
                            status_byte = format(read[2], '08b')
                            #~ print("Status byte (low & high):", status_byte[2], status_byte[3], status_byte)
                            if status_byte[2] == 1 or status_byte[3] == 1 or read[3:6] == [127,255,255] or read[3:6] == [128,0,0]:
                                print("Error. PGA Alarm.", self.check_status())
                                return "Error. PGA alarm."
                            else:
                                response = self.convert_to_mV(read[3:6], reference = reference, gain = gain)
                        elif status == 'disabled' and crc == 'disabled':
                            response = self.convert_to_mV(read[2:5], reference = reference, gain = gain)
                        elif status != 'disabled' and crc != 'disabled':
                            out_crc2, status_byte = read[3], format(read[2], '08b')
                            response = self.convert_to_mV(read[5:8], reference = reference, gain = gain)
                            out_crc3 = read[8]
                        elif status == 'disabled' and crc != 'disabled':
                            out_crc2 = read[3]
                            response = self.convert_to_mV(read[4:7], reference = reference, gain = gain)
                            out_crc3 = read[8]
                        else:
                            print("Error in collect_measurement - status or crc not 'disabled'.")
                        if response not in [None, 'None']:
                            response = float(response)
                            return response
                        else:
                            response = -1        
                    else:
                        response = -1
                                                                          
                except KeyboardInterrupt:
                     
                except: 
                    i+=1
                    pass

        elif method.lower() == 'software':
            DRDY_status = 'not new'
            while DRDY_status.lower() != 'new':
                if i > 1000:  
                try:
                    LOCK_status, CRCERR_status, PGAL_ALM_status, PGAH_ALM_status, REFL_ALM_status, DRDY_status, CLOCK_status, RESET_status = self.check_status()
                    if DRDY_status.lower() == 'new':
                        read = self.send(rdata)
                        response = self.convert_to_mV(read[2:5], reference = reference, gain = gain)
                        return response
                    else:
                        pass
                except KeyboardInterrupt:
                     
                except: 
                    print("Wow! No new conversion??")
                    i+=1
                    pass
        else:
            print("Missing method to collect measurement. Please select either 'hardware' or 'software'.")
            
        
    
    def convert_to_mV(self, array, reference = 5000, gain = 1):
        # Only for use without CRC checking!!
        #use twos complement online to check
        MSB, MID, LSB = array
        bit24 = (MSB<<16)+(MID<<8)+LSB
        #~ print("bit24:", bit24)
        if MSB>127: # i.e. signed negative
            bits_from_fullscale = (2**24-bit24)
            #~ print(bits_from_fullscale, reference, gain)
            mV = -bits_from_fullscale*reference/(gain*2**23)
            #~ print(mV)
        else:
            mV = bit24*reference/(gain*2**23)
        #~ print("mV:", mV)
        return mV
        
    
    def check_temperature(self):
        # Table 7.5: Electrical Characteristics 
        # When the internal temperature is 25 deg C, the output is 122.4 mV. 
        # The temperature coefficient is 0.42 mV/C.
        #~ power = self.power_readback()
        # self.reset()
        # Turn PGA on with gain = 1
        BYPASS_status, gain = self.check_PGA()
        self.PGA(BYPASS=0, GAIN = int(1))
        
        # Burn-out current sources disabled
        Vbias, polarity, magnitude = self.check_burn_out_current_source()
        self.burn_out_current_source(VBIAS = 'disabled', polarity = 'pull-up mode', magnitude = 'off')
        
        # AC-excitation mode disabled
        CHOP, CONVRT, DELAY = self.check_mode1()
        self.mode1()
        PWDN_status, STATENB_status, CRCENB_status, SPITIM_status, GPIO3_status, GPIO2_status, GPIO1_status, GPIO0_status = self.check_mode3()
        self.mode3()

        ref_enable_status, RMUXP_status, RMUXN_status = self.check_reference_config()
        self.reference_config()
        
        #Select relevant inputs
        self.choose_inputs(positive = 'INTEMPSENSE', negative = 'INTEMPSENSE')
        
        self.start1()
        #~ time.sleep(0.1)
        response = 'none'
        i = 0
        while(type(response) != float and i < 1000):
            try:
                response = self.collect_measurement(method='hardware', reference = 5000, gain = 1)
                i += 1
            except KeyboardInterrupt:
                 
        #~ temperature = (response - 111.9)/0.42
        #~ print("Temperature (mV):", response)
        temperature = (response - 122.4)/0.42+25
        
        # Reinstate previous settings
        # Burn out current source
        self.burn_out_current_source(Vbias, polarity, magnitude)
        
        # Programmable gain amplifier settings
        self.PGA(BYPASS_status, gain)
        
        # AC-excitation setings
        self.mode1(CHOP, CONVRT, DELAY)
        self.mode3(PWDN_status, STATENB_status, CRCENB_status, SPITIM_status, GPIO3_status, GPIO2_status, GPIO1_status, GPIO0_status)
        
        # Reference configuration (internal reference, etc)
        self.reference_config(ref_enable_status, RMUXP_status, RMUXN_status)
        #~ time.sleep(0.1)
        return temperature
        
    def current_out_magnitude(self, current1 = 'off', current2 = 'off'):
        #print("Current magnitude activated")
        # The internal reference MUST be enabled for this function to work!!
        p,n = self.check_reference_config()[-2:]
        self.reference_config(1, p,n)
        print("Internal 2.5 V reference enabled for current output, per 9.3.6 in datasheet.")
        # current must be in uA
        current1 = str(current1)
        current2 = str(current2)
        if (current1 in self.IMAG_register) and (current2 in self.IMAG_register):
            current2_IMAG = int(self.IMAG_register[current2]<<4)
            current1_IMAG = int(self.IMAG_register[current1])
            bits = current2_IMAG + current1_IMAG
            message = format(bits,'08b')
            self.write_register('IMAG', message)
        else:
            if (current1 not in self.IMAG_register):
                print("IMAG value not available.\nYou requested",current1,"but only",str(list(self.IMAG_register.keys())),"are available in uA.")
            elif (current2 not in self.IMAG_register):
                print("IMAG value not available.\nYou requested",current2,"but only",str(list(self.IMAG_register.keys())),"are available in uA.")
             
        
        return current1, current2
    
    def current_out_pin(self, IMUX1 = 'NONE', IMUX2 = 'NONE'):
        #print("Current pin activated")
        IMUX1 = str(IMUX1).upper()
        IMUX2 = str(IMUX2).upper()
        if IMUX1 == IMUX2 and IMUX1 != 'NONE':
            print("IMUX1 and IMUX2 are both the same pin. They must either be different output pins, or both be 'NONE'.")
            #  
        p,n = self.check_reference_config()[-2:]
        self.reference_config(1, p,n)
        #~ print("Internal 2.5 V reference enabled for current output.")
        if IMUX1 in self.OUTPMUXregister:
            if IMUX2 in self.OUTPMUXregister:
                IMUX2_bits = int(self.OUTPMUXregister[IMUX2]<<4)
                IMUX1_bits = int(self.OUTPMUXregister[IMUX1])
                bits = IMUX2_bits + IMUX1_bits
                message = format(bits,'08b')
                self.write_register('IMUX', message)
            else:
                print("IMUX2 value not available.\nYou requested '" + IMUX2 + "' but only "+str(list(self.OUTPMUXregister.keys()))+" are available.")
                 
        else:
            print("IMUX1 value not available.\nYou requested '" + IMUX1 + "' but only "+str(list(self.OUTPMUXregister.keys()))+" are available.")
             
    
        return IMUX1, IMUX2
        
    def power_readback(self, power = 'analog'):
        ''' Returns the power between AVDD & AVSS or DVDD & DVSS in mV. 
        Power can be 'analog' or 'digital'. '''
        self.setup_measurements()
        data_rate, digital_filter = self.check_frequency(print_freq = False)
        # Turn PGA on with gain = 1
        self.PGA(BYPASS=0, GAIN = int(1))
        # Burn-out current sources disabled
        self.burn_out_current_source(VBIAS = 'disabled', polarity = 'pull-up mode', magnitude = 'off')
        # AC-excitation mode disabled
        self.mode1(); self.mode2(); self.mode3()
        self.reference_config(reference_enable = 1, RMUXP = 'Internal Positive', RMUXN = 'Internal Negative')
        #~ self.reference_config(reference_enable = 1, RMUXP = 'AVDD', RMUXN = 'AVSS')
#        self.print_reference_config()
        
        # Declare the pins
        if power == 'analog':
            self.choose_inputs(positive = 'INTAV4', negative = 'INTAV4')
        else:
            self.choose_inputs(positive = 'INTDV4', negative = 'INTDV4')
        
        self.set_frequency(data_rate = 7200, digital_filter = 'sinc1', print_freq = False)
        
        # Measure the potential
        self.start1()
        response = None
        error = 0
        samples = []
        
        while(type(response) != float and error < 1000 and len(samples) < 10):
            try:
                response = self.collect_measurement(method='hardware', reference = 2500, gain = 1)
                
                if type(response) == float and response != None:
#                    print(response, type(response), len(samples))
                    samples.append(response*4)
                response = None
            except KeyboardInterrupt:
                 
            except:
                error += 1
        # return to previous frequency and filter
        self.set_frequency(data_rate = data_rate, digital_filter = digital_filter, print_freq = False)
        return self.median(samples)

def main():
    return 0
    
if __name__ == "__main__":
    main()