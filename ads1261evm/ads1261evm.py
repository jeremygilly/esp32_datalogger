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
        (40000, int('10000',2))
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
    
    inv_registerAddress = {v: k for k, v in registerAddress.items()}
    inv_INPMUXregister = {v: k for k, v in INPMUXregister.items()}
    inv_available_data_rates = {v: k for k, v in available_data_rates.items()}
    inv_available_digital_filters = {v: k for k, v in available_digital_filters.items()}
    inv_available_gain = {v: k for k, v in available_gain.items()}
    inv_available_reference = {v: k for k, v in available_reference.items()}
    inv_mode1register = {v: k for k, v in mode1register.items()}
    
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
            print('Send failed.', e)
            print(wbuf, rbuf)
            print ("Attempted byte message:", wbuf)

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
            returnedMessage = self.send(hex_message=read_message)
            return returnedMessage[2]
        else: 
            pass

    def write_register(self, register_location, register_data):
        # expects to see register_location as a human readable string
        register_location = register_location.upper()
        # expects to see register_data as a binary string
        if not isinstance(register_data, str):
            register_data = format(register_data,'08b')
        
        hex_message = [self.commandByte1['WREG'][0]+self.registerAddress[register_location],int(register_data,2),0,0,0]
        
        read_message = hex_message
        
        write_check = self.send(read_message)
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
        return self.check_frequency(print_freq=print_freq)
        
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
        return self.check_status()
        
    def check_status(self):
        read = self.read_register('STATUS')
        byte_string = list(map(int,format(read,'08b')))
        LOCK_status, CRCERR_status, PGAL_ALM_status, PGAH_ALM_status, REFL_ALM_status, DRDY_status, CLOCK_status, RESET_status = byte_string
        return LOCK_status, CRCERR_status, PGAL_ALM_status, PGAH_ALM_status, REFL_ALM_status, DRDY_status, CLOCK_status, RESET_status
 
    def mode1(self, CHOP = 'normal', CONVRT = 'continuous', DELAY = '50us'):
        # CHOP = 'normal', 'chop', '2-wire ac-excitation', or '4-wire ac-excitation'
        # CONVRT = 'continuous' or 'pulse'
        # DELAY = '0us', '50us', '59us', '67us', '85us', '119us','189us', '328us','605us','1.16ms','2.27ms','4.49ms','8.93ms', or '17.8ms'
        [CHOP, CONVRT, DELAY] = [CHOP.lower(), CONVRT.lower(), DELAY.lower()] # formatting
        send_mode1 = self.mode1register[CHOP]+self.mode1register[CONVRT]+self.mode1register[DELAY]
        send_mode1 = format(send_mode1, '08b')
        self.write_register('MODE1', send_mode1)
        return self.check_mode1()
        
    def check_mode1(self):
        read = self.read_register('MODE1')
        byte_string = list(map(int,format(read,'08b')))#; print(byte_string)
        chop_bits = int(''.join(map(str,byte_string[1:3])),2)<<5
        convrt_bits = int(str(byte_string[3]),2)<<4
        CHOP = 'normal' if chop_bits == 0 else self.inv_mode1register[chop_bits]
        CONVRT = 'continuous' if convrt_bits == 0 else self.inv_mode1register[int(str(byte_string[3]),2)<<4]
        DELAY = self.inv_mode1register[int(''.join(map(str,byte_string[4:])),2)]
        return CHOP, CONVRT, DELAY

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
        try:
            byte_string = list(map(int,format(read,'08b')))
            PWDN_status, STATENB_status, CRCENB_status, SPITIM_status, GPIO3_status, GPIO2_status, GPIO1_status, GPIO0_status = byte_string
            return PWDN_status, STATENB_status, CRCENB_status, SPITIM_status, GPIO3_status, GPIO2_status, GPIO1_status, GPIO0_status
        except Exception as e:
            print(e)
            print(type(read), read)
                
    def PGA(self, BYPASS = 0, GAIN = 1):
        # BYPASS can be 0 (PGA mode (default)) or 1 (PGA  bypass).
        send_PGA = int(BYPASS<<7)+int(self.available_gain[GAIN])
        send_PGA = format(send_PGA, '08b')
        self.write_register('PGA', send_PGA)
        return self.check_PGA()
        
    def check_PGA(self):
        read = self.read_register('PGA')
        byte_string = list(map(int,format(read,'08b')))
        BYPASS_status = 0 if byte_string[0] == 0 else 1
        gain = self.inv_available_gain[int(''.join(map(str,byte_string[5:])),2)]
        return BYPASS_status, gain

    def reference_config(self, reference_enable = 0, RMUXP = 'AVDD', RMUXN = 'AVSS'):
        # Note: Bit shifting not required when referencing dictionary (already happens at the dictionary level).
        # reference_enable must be 0 (disabled) or 1 (enabled)
        # RMUXP is the reference positive side, can be "Internal Positive", "AVDD", "AIN0", or "AIN2"
        # RMUXN is the reference negative side, can be "Internal Negative", "AVSS", "AIN1", or "AIN3"
        send_ref_config = int(reference_enable<<4) + self.available_reference[RMUXP] + self.available_reference[RMUXN]
        send_ref_config = format(send_ref_config, '08b')
        self.write_register('REF', send_ref_config)
        return self.check_reference_config()
        
    def check_reference_config(self):
        read = self.read_register('REF')
        byte_string = list(map(int,format(read,'08b')))
        ref_enable_status = 0 if byte_string[3] == 0 else 1
        RMUXP_status = self.inv_available_reference[int(''.join(map(str,byte_string[4:6])),2)<<2]
        RMUXN_status = self.inv_available_reference[int(''.join(map(str,byte_string[6:])),2)]
        return ref_enable_status, RMUXP_status, RMUXN_status
                
    def calibration(self, calibration = "SFOCAL"):
        # User offset calibration not implemented.
        calibration = [self.commandByte1[calibration][0], self.arbitrary, self.zero]
        return self.send(calibration)
        
    def setup_measurements(self):
        #~ Based on Figure 101 in ADS1261 data sheet
        #~ Set reset and PWDN pins high
        self.rst.on()
        self.pwdn.on()
        self.start.on()
        return 0
        
    def reset(self):
        self.rst.off()
        time.sleep(0.1)
        self.rst.on()
        return 0
    
    def syocal(self):
        print("Please ensure inputs are shorted together")
        self.start1()
        syocal_message = [self.commandByte1['SYOCAL'][0], self.arbitrary]
        # delay for calibration time: Table 14, pg 49, ADS1261 data sheet
        self.send(syocal_message)
        return 0
    
    def sfocal(self):
        self.start1()
        sfocal_message = [self.commandByte1['SFOCAL'][0], self.arbitrary]
        self.send(sfocal_message)
        return 0
    
    def stop(self):
        stop_message = [self.commandByte1['STOP'][0], self.arbitrary, self.zero]
        self.send(stop_message)
        return 0
        
    def start1(self):
        start_message = [self.commandByte1['START'][0], self.arbitrary, self.zero]
        self.send(start_message)
        return 0

    def median(l):
        if len(l) % 2 == 0:
                return (l[int(len(l)/2-1)] + l[int(len(l)/2)]) / 2
        else:
                return l[int(len(l)/2)]
    
    def status(self, status_byte):
        PWDN_status, STATENB_status, CRCENB_status, SPITIM_status, GPIO3_status, GPIO2_status, GPIO1_status, GPIO0_status = status_byte
        return 0
    

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
                     sys.exit(1)
                except Exception as e: 
                    i+=1
                    pass

        elif method.lower() == 'software':
            DRDY_status = 'not new'
            while DRDY_status.lower() != 'new':
                if i > 1000: sys.exit(1)
                try:
                    LOCK_status, CRCERR_status, PGAL_ALM_status, PGAH_ALM_status, REFL_ALM_status, DRDY_status, CLOCK_status, RESET_status = self.check_status()
                    if DRDY_status.lower() == 'new':
                        read = self.send(rdata)
                        response = self.convert_to_mV(read[2:5], reference = reference, gain = gain)
                        return response
                    else:
                        pass
                except KeyboardInterrupt:
                     sys.exit(1)
                except: 
                    print("Wow! No new conversion??")
                    i+=1
                    pass
        else:
            print("Missing method to collect measurement. Please select either 'hardware' or 'software'.")
        
    def convert_to_mV(self, array, reference = 5000, gain = 1):
        MSB, MID, LSB = array
        bit24 = (MSB<<16)+(MID<<8)+LSB
        if MSB>127: # i.e. signed negative
            bits_from_fullscale = (2**24-bit24)
            mV = -bits_from_fullscale*reference/(gain*2**23)
        else:
            mV = bit24*reference/(gain*2**23)
        return mV

def main():
    return 0
    
if __name__ == "__main__":
    main()
