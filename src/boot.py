import sys

if sys.platform in ['trezor', 'pyboard']: # stmhal
    import pyb
    # hid=(subclass, protocol, max_packet_len, polling_interval, report_desc)
    pyb.usb_mode('CDC+HID', vid=0x1209, pid=0x53C1, hid=(0, 0, 64, 1, b'\x06\x00\xff\x09\x01\xa1\x01\x09\x20\x15\x00\x26\xff\x00\x75\x08\x95\x40\x81\x02\x09\x21\x15\x00\x26\xff\x00\x75\x08\x95\x40\x91\x02\xc0'))
