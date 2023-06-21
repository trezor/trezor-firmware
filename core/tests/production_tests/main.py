import utime

import trezorio as io
import trezorui as ui

usb_vcp = io.VCP(
    iface_num=0x00,
    data_iface_num=0x01,
    ep_in=0x81,
    ep_out=0x01,
    ep_cmd=0x82,
)

usb = io.USB(
    vendor_id=0x1209,
    product_id=0x53C1,
    release_num=0x0200,
    manufacturer="SatoshiLabs",
    product="TREZOR",
    serial_number="000000000000000000000000",
    usb21_landing=False,
)

usb.add(usb_vcp)

usb.open()

d = ui.Display()
otp = io.FlashOTP()
sd = io.SDCard()
sbu = io.SBU()


def test_display(colors):
    d.clear()
    m = {
        'R': 0xF800,
        'G': 0x07E0,
        'B': 0x001F,
        'W': 0xFFFF,
    }
    w = 240 // len(colors)
    for i, c in enumerate(colors):
        c = m.get(c, 0x0000)
        d.bar(i * w, 0, i * w + w, 240, c)
    d.refresh()
    print('OK')


def test_touch(v):
    d.clear()
    c, t = int(v[0]), int(v[1])
    deadline = utime.ticks_add(utime.ticks_us(), t * 1000000)
    if c == 1:
        d.bar(0, 0, 120, 120, 0xFFFF)
    elif c == 2:
        d.bar(120, 0, 120, 120, 0xFFFF)
    elif c == 3:
        d.bar(120, 120, 120, 120, 0xFFFF)
    else:
        d.bar(0, 120, 120, 120, 0xFFFF)
    d.refresh()
    r = [0, 0]
    # flush all events
    while io.poll([io.TOUCH], r, 10000):
        pass
    # wait for event
    touch = False
    while True:
        if not touch:
            if io.poll([io.TOUCH], r, 10000) and r[0] == io.TOUCH and r[1][0] == io.TOUCH_START:
                touch = True
        else:
            if io.poll([io.TOUCH], r, 10000) and r[0] == io.TOUCH and r[1][0] == io.TOUCH_END:
                print(f'OK {r[1][1]} {r[1][2]}')
                break
        if utime.ticks_us() > deadline:
            print('ERROR TIMEOUT')
            break
    # flush all events
    while io.poll([io.TOUCH], r, 10000):
        pass
    d.clear()
    d.refresh()


def test_pwm(v):
    d.backlight(int(v))
    d.refresh()
    print('OK')


def test_sd():
    if sd.present():
        sd.power(True)
        buf1 = bytearray(8 * 1024)
        try:
            sd.read(0, buf1)
        except OSError:
            print('ERROR READING DATA')
            sd.power(False)
            return
        try:
            sd.write(0, buf1)
        except OSError:
            print('ERROR WRITING DATA')
            sd.power(False)
            return
        buf2 = bytearray(8 * 1024)
        try:
            sd.read(0, buf2)
        except OSError:
            print('ERROR READING DATA')
            sd.power(False)
            return
        if buf1 == buf2:
            print('OK')
        else:
            print('ERROR DATA MISMATCH')
        sd.power(False)
    else:
        print('ERROR NOCARD')


def test_sbu(v):
    sbu1 = (v[0] == '1')
    sbu2 = (v[1] == '1')
    sbu.set(sbu1, sbu2)
    print('OK')


def test_otp_read():
    data = bytearray(32)
    otp.read(0, 0, data)
    data = bytes(data).rstrip(b'\x00\xff').decode()
    print('OK', data)


def test_otp_write(v):
    if len(v) < 32:
        v = v + '\x00' * (32 - len(v))
    data = v[:32].encode()
    otp.write(0, 0, data)
    otp.lock(0)
    print('OK')


d.clear()

while True:

    try:
        line = input()

        if line == 'PING':
            print('OK')

        elif line.startswith('DISP '):
            test_display(line[5:])

        elif line.startswith('TOUCH '):
            test_touch(line[6:])

        elif line.startswith('PWM '):
            test_pwm(line[4:])

        elif line == 'SD':
            test_sd()

        elif line.startswith('SBU '):
            test_sbu(line[4:])

        elif line.startswith('OTP READ'):
            test_otp_read()

        elif line.startswith('OTP WRITE '):
            test_otp_write(line[10:])

        else:
            print('UNKNOWN')

    except Exception as ex:
        print('ERROR', ex)
