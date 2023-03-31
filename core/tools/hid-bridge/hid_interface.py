import os

import logger
import uhid


def random_bytes(length):
    return os.urandom(length)


class HIDInterface:
    uhid_device = "/dev/uhid"

    def __init__(self):
        self.file_descriptor = os.open(HIDInterface.uhid_device, os.O_RDWR)
        self.create_device()

    def __uhid_read(self, length):
        data = os.read(self.file_descriptor, length)
        logger.log_raw(f"{HIDInterface.uhid_device} >", data.hex())
        return data

    def __uhid_write(self, data):
        bytes_written = os.write(self.file_descriptor, data)
        assert bytes_written == len(data)
        logger.log_raw(f"{HIDInterface.uhid_device} <", data.hex())

    def create_device(self):
        name = b"Virtual Trezor"
        phys = b""
        uniq = random_bytes(64)
        bus = 0
        vendor = 0x1209
        product = 0x53C1
        version = 0x0200
        country = 0
        # fmt: off
        rd_data = bytes([
            0x06, 0xD0, 0xF1,  # USAGE_PAGE (FIDO Alliance)
            0x09, 0x01,        # USAGE (U2F HID Authenticator Device)
            0xA1, 0x01,        # COLLECTION (Application)
            0x09, 0x20,        # USAGE (Input Report Data)
            0x15, 0x00,        # LOGICAL_MINIMUM (0)
            0x26, 0xFF, 0x00,  # LOGICAL_MAXIMUM (255)
            0x75, 0x08,        # REPORT_SIZE (8)
            0x95, 0x40,        # REPORT_COUNT (64)
            0x81, 0x02,        # INPUT (Data,Var,Abs)
            0x09, 0x21,        # USAGE (Output Report Data)
            0x15, 0x00,        # LOGICAL_MINIMUM (0)
            0x26, 0xFF, 0x00,  # LOGICAL_MAXIMUM (255)
            0x75, 0x08,        # REPORT_SIZE (8)
            0x95, 0x40,        # REPORT_COUNT (64)
            0x91, 0x02,        # OUTPUT (Data,Var,Abs)
            0xC0,              # END_COLLECTION
        ])
        # fmt: on

        buf = uhid.create_create2_event(
            name, phys, uniq, bus, vendor, product, version, country, rd_data
        )
        self.__uhid_write(buf)
        logger.log_uhid_event(
            "UHID_CREATE2",
            f"name='{name.decode()}' "
            f"phys='{phys.decode()}' "
            f"uniq=0x{uniq.hex()} "
            f"rd_size={len(rd_data)} "
            f"bus=0x{bus:04x} "
            f"vendor=0x{vendor:04x} "
            f"product=0x{product:04x} "
            f"version=0x{version:04x} "
            f"country=0x{country:04x} "
            f"rd_data=0x{rd_data.hex()}",
        )

    def write_data(self, data):
        buf = uhid.create_input2_event(data)
        self.__uhid_write(buf)
        logger.log_uhid_event(
            "UHID_INPUT2", f"data=0x{data.hex()} size={len(data)}"
        )
        logger.log_hid_packet("DEVICE_OUTPUT", f"0x{data.hex()}")

    def process_event(self):
        ev_type, request = uhid.parse_event(self.__uhid_read(uhid.EVENT_LENGTH))
        if ev_type == uhid.EVENT_TYPE_START:
            dev_flags, = request
            logger.log_uhid_event("UHID_START", f"dev_flags=0b{dev_flags:08b}")
        elif ev_type == uhid.EVENT_TYPE_STOP:
            logger.log_uhid_event("UHID_STOP")
        elif ev_type == uhid.EVENT_TYPE_OPEN:
            logger.log_uhid_event("UHID_OPEN")
        elif ev_type == uhid.EVENT_TYPE_CLOSE:
            logger.log_uhid_event("UHID_CLOSE")
        elif ev_type == uhid.EVENT_TYPE_OUTPUT:
            data, size, rtype = request
            logger.log_uhid_event(
                "UHID_OUTPUT",
                f"data=0x{data.hex()} size={size} rtype={rtype}",
            )
            logger.log_hid_packet("DEVICE_INPUT", f"0x{data[1:].hex()}")
            return data[1:]
        else:
            logger.log_uhid_event(
                "UNKNOWN_EVENT",
                f"ev_type={ev_type} request=0x{request.hex()}",
            )
