

    def convert_to_mV(self, array, reference=5000, gain=1):
        MSB, MID, LSB = array
        bit24 = (MSB << 16) + (MID << 8) + LSB
        if MSB > 127:  # i.e. signed negative
            bits_from_fullscale = 2 ** 24 - bit24
            mV = -bits_from_fullscale * reference / (gain * 2 ** 23)
        else:
            mV = bit24 * reference / (gain * 2 ** 23)
        return mV



    def choose_inputs(self, positive, negative="VCOM"):
        # 01100111 - AIN5-6
        input_pins = "01000101"

        return self.write_register(0x11, "01000101")
        # self.check_inputs()

        read_message = [0x40 + 0x11, 0x45, 0, 0, 0]
        self.send(read_message)

        wbuf = bytes(byte_message)
        rbuf = bytearray(5)
        self.spi.write_readinto(wbuf, rbuf)


("AIN3", int("0100", 2)),
            ("AIN4", int("0101", 2)),
            ("AIN5", int("0110", 2)),
            ("AIN6", int("0111", 2)),

def test2():
    wbuf1 = bytes([0x51, 0x45, 0, 0, 0])
    wbuf2 = bytes([0x51, 0x67, 0, 0, 0])
    rbuf = bytearray(5)
    for i in range(1000):
        adc.spi.write_readinto(wbuf1, rbuf)
        adc.spi.write_readinto(wbuf2, rbuf)

def test4():
    rdata = [0x12, 0, 0, 0, 0, 0, 0, 0, 0]
    wbuf = bytes(rdata)
    if not adc.drdy.value():
        
        rbuf = bytearray(len(wbuf))
        adc.spi.write_readinto(wbuf, rbuf)
        response = adc.convert_to_mV(rbuf[2:5], reference=5000, gain=1)

def test8():
    all_results_a, all_results_b = [], []
    wbuf1, wbuf2, rdata = bytes([0x51, 0x45, 0, 0, 0]), bytes([0x51, 0x67, 0, 0, 0]), bytes([0x12, 0, 0, 0, 0])
    for i in range(1000):
        adc.spi.write_readinto(wbuf1, rbuf)
        adc.start.on()
        if not adc.drdy.value():
            adc.spi.write_readinto(b'\x12\x00\x00\x00\x00', rbuf)
            adc.start.off()
            all_results_a.append(rbuf)
            
        # adc.spi.write_readinto(wbuf2, rbuf)
        # adc.spi.write_readinto(b'\x12\x00\x00\x00\x00', rbuf)
        # all_results_b.append(rbuf)

