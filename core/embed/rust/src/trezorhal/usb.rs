use cstr_core::CStr;
use heapless::Vec;

use crate::trezorhal::secbool;

use super::ffi;

const MAX_IFACE_COUNT: usize = 4;

pub enum UsbError {
    FailedToAddInterface,
    InterfaceNotFound,
    Io,
}

pub struct Usb {
    config: UsbConfig,
}

pub enum Interest {
    Read,
    Write,
}

pub enum Event {
    Ready,
    Pending,
}

impl Usb {
    pub fn open(mut config: UsbConfig) -> Result<Self, UsbError> {
        // SAFETY:
        unsafe { ffi::usb_init(&config.as_dev_info()) };

        for iface in &mut config.interfaces {
            let res = match iface {
                IfaceConfig::Hid(hid) => hid.register(),
                IfaceConfig::WebUsb(wusb) => wusb.register(),
            };
            if let Err(err) = res {
                // SAFETY:
                unsafe { ffi::usb_deinit() };

                return Err(err);
            }
        }

        // SAFETY:
        unsafe { ffi::usb_start() };

        Ok(Self { config })
    }

    pub fn poll(&mut self, iface_num: u8, interest: Interest) -> Result<Event, UsbError> {
        let iface = self.config.find_iface(iface_num)?;

        let ready = match iface {
            IfaceConfig::Hid(hid) => match interest {
                Interest::Read => hid.ready_to_read(),
                Interest::Write => hid.ready_to_write(),
            },
            IfaceConfig::WebUsb(wusb) => match interest {
                Interest::Read => wusb.ready_to_read(),
                Interest::Write => wusb.ready_to_write(),
            },
        };

        Ok(if ready { Event::Ready } else { Event::Pending })
    }

    pub fn read(&mut self, iface_num: u8, buffer: &mut [u8]) -> Result<usize, UsbError> {
        let iface = self.config.find_iface(iface_num)?;

        match iface {
            IfaceConfig::Hid(hid) => hid.read(buffer),
            IfaceConfig::WebUsb(wusb) => wusb.read(buffer),
        }
    }

    pub fn write(&mut self, iface_num: u8, buffer: &[u8]) -> Result<usize, UsbError> {
        let iface = self.config.find_iface(iface_num)?;

        match iface {
            IfaceConfig::Hid(hid) => hid.write(buffer),
            IfaceConfig::WebUsb(wusb) => wusb.write(buffer),
        }
    }

    pub fn close(self) {
        // SAFETY:
        unsafe { ffi::usb_stop() };

        // SAFETY:
        unsafe { ffi::usb_deinit() };
    }
}

pub struct UsbConfig {
    pub vendor_id: u16,
    pub product_id: u16,
    pub release_num: u16,
    pub manufacturer: &'static CStr,
    pub product: &'static CStr,
    pub serial_number: &'static CStr,
    pub interface: &'static CStr,
    pub usb21_landing: bool,
    pub interfaces: Vec<IfaceConfig, MAX_IFACE_COUNT>,
}

impl UsbConfig {
    fn as_dev_info(&self) -> ffi::usb_dev_info_t {
        ffi::usb_dev_info_t {
            device_class: 0,
            device_subclass: 0,
            device_protocol: 0,
            vendor_id: self.vendor_id,
            product_id: self.product_id,
            release_num: self.release_num,
            manufacturer: self.manufacturer.as_ptr(),
            product: self.product.as_ptr(),
            serial_number: self.serial_number.as_ptr(),
            interface: self.interface.as_ptr(),
            usb21_enabled: secbool::TRUE,
            usb21_landing: if self.usb21_landing {
                secbool::TRUE
            } else {
                secbool::FALSE
            },
        }
    }

    fn find_iface(&mut self, iface_num: u8) -> Result<&mut IfaceConfig, UsbError> {
        self.interfaces
            .iter_mut()
            .find(|iface| match iface {
                IfaceConfig::Hid(hid) => hid.iface_num == iface_num,
                IfaceConfig::WebUsb(wusb) => wusb.iface_num == iface_num,
            })
            .ok_or(UsbError::InterfaceNotFound)
    }
}

pub enum IfaceConfig {
    Hid(HidConfig),
    WebUsb(WebUsbConfig),
}

pub struct HidConfig {
    pub report_desc: &'static [u8],
    pub rx_buffer: &'static mut [u8],
    pub iface_num: u8,
    pub emu_port: u16,
    pub ep_in: u8,
    pub ep_out: u8,
}

impl HidConfig {
    fn register(&mut self) -> Result<(), UsbError> {
        // SAFETY:
        let res = unsafe { ffi::usb_hid_add(&self.as_hid_info()) };

        if res != secbool::TRUE {
            Err(UsbError::FailedToAddInterface)
        } else {
            Ok(())
        }
    }

    fn ready_to_read(&mut self) -> bool {
        // SAFETY:
        unsafe { ffi::usb_hid_can_read(self.iface_num) == secbool::TRUE }
    }

    fn ready_to_write(&mut self) -> bool {
        // SAFETY:
        unsafe { ffi::usb_hid_can_write(self.iface_num) == secbool::TRUE }
    }

    fn read(&mut self, buffer: &mut [u8]) -> Result<usize, UsbError> {
        // SAFETY:
        let result =
            unsafe { ffi::usb_hid_read(self.iface_num, buffer.as_mut_ptr(), buffer.len() as u32) };

        if result < 0 {
            Err(UsbError::Io)
        } else {
            Ok(result as usize)
        }
    }

    fn write(&mut self, buffer: &[u8]) -> Result<usize, UsbError> {
        // SAFETY:
        let result =
            unsafe { ffi::usb_hid_write(self.iface_num, buffer.as_ptr(), buffer.len() as u32) };

        if result < 0 {
            Err(UsbError::Io)
        } else {
            Ok(result as usize)
        }
    }

    fn as_hid_info(&mut self) -> ffi::usb_hid_info_t {
        ffi::usb_hid_info_t {
            report_desc: self.report_desc.as_ptr(), // With length of report_desc_len bytes.
            report_desc_len: self.report_desc.len() as u8, // Length of report_desc.
            rx_buffer: self.rx_buffer.as_mut_ptr(), // With length of max_packet_len bytes.
            max_packet_len: self.rx_buffer.len() as u8, // Length of the biggest report and of rx_buffer.
            iface_num: self.iface_num,                  // Address of this HID interface.
            // emu_port: self.emu_port, // UDP port of this interface in the emulator.
            ep_in: self.ep_in, // Address of IN endpoint (with the highest bit set).
            ep_out: self.ep_out, // Address of OUT endpoint.
            subclass: 0,       // usb_iface_subclass_t
            protocol: 0,       // usb_iface_protocol_t
            polling_interval: 1, // In units of 1ms.
        }
    }
}

pub struct WebUsbConfig {
    pub rx_buffer: &'static mut [u8],
    pub iface_num: u8,
    pub emu_port: u16,
    pub ep_in: u8,
    pub ep_out: u8,
}

impl WebUsbConfig {
    fn register(&mut self) -> Result<(), UsbError> {
        // SAFETY:
        let res = unsafe { ffi::usb_webusb_add(&self.as_webusb_info()) };

        if res != secbool::TRUE {
            Err(UsbError::FailedToAddInterface)
        } else {
            Ok(())
        }
    }

    fn ready_to_read(&mut self) -> bool {
        // SAFETY:
        unsafe { ffi::usb_webusb_can_read(self.iface_num) == secbool::TRUE }
    }

    fn ready_to_write(&mut self) -> bool {
        // SAFETY:
        unsafe { ffi::usb_webusb_can_write(self.iface_num) == secbool::TRUE }
    }

    fn read(&mut self, buffer: &mut [u8]) -> Result<usize, UsbError> {
        // SAFETY:
        let result = unsafe {
            ffi::usb_webusb_read(self.iface_num, buffer.as_mut_ptr(), buffer.len() as u32)
        };

        if result < 0 {
            Err(UsbError::Io)
        } else {
            Ok(result as usize)
        }
    }

    fn write(&mut self, buffer: &[u8]) -> Result<usize, UsbError> {
        // SAFETY:
        let result =
            unsafe { ffi::usb_webusb_write(self.iface_num, buffer.as_ptr(), buffer.len() as u32) };

        if result < 0 {
            Err(UsbError::Io)
        } else {
            Ok(result as usize)
        }
    }

    fn as_webusb_info(&mut self) -> ffi::usb_webusb_info_t {
        ffi::usb_webusb_info_t {
            rx_buffer: self.rx_buffer.as_mut_ptr(), // With length of max_packet_len bytes.
            max_packet_len: self.rx_buffer.len() as u8, // Length of the biggest report and of rx_buffer.
            iface_num: self.iface_num,                  // Address of this WebUSB interface.
            // emu_port: self.emu_port, // UDP port of this interface in the emulator.
            ep_in: self.ep_in, // Address of IN endpoint (with the highest bit set).
            ep_out: self.ep_out, // Address of OUT endpoint.
            subclass: 0,       // usb_iface_subclass_t
            protocol: 0,       // usb_iface_protocol_t
            polling_interval: 1, // In units of 1ms.
        }
    }
}
