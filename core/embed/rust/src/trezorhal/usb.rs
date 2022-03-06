use cstr_core::CStr;
use heapless::Vec;

use crate::trezorhal::secbool;

use super::ffi;

#[derive(Debug)]
pub enum UsbError {
    /// Failed to register USB interface configuration.
    FailedToAddInterface,
    /// Interface number not found, or found with an invalid type.
    InterfaceNotFound,
}

pub enum Interest {
    /// Caller is interested to read bytes/messages.
    Read,
    /// Caller is interested to write bytes/messages.
    Write,
}

pub enum Event {
    /// Resource is ready to perform on selected `Interest`.
    Ready,
    /// Resource is not yet ready. No side-effect was performed.
    Pending,
}

/// Initialize the USB stack with information from `config`, register all
/// present USB interfaces, and start the communication.
///
/// Should be called only with the USB closed.
///
/// Returns error in case any interface registration fails.
///
/// USB stack should be shut down and de-initialized with `usb_close` when not
/// needed.
pub fn usb_open(mut config: UsbConfig) -> Result<(), UsbError> {
    // SAFETY: All values in `config` should have static lifetime.
    unsafe { ffi::usb_init(&config.as_dev_info()) };

    for iface in &mut config.interfaces {
        let res = match iface {
            IfaceConfig::Vcp(vcp) => vcp.register(),
            IfaceConfig::Hid(hid) => hid.register(),
            IfaceConfig::WebUsb(wusb) => wusb.register(),
        };
        if let Err(err) = res {
            // SAFETY: No other invariants.
            unsafe { ffi::usb_deinit() };

            return Err(err);
        }
    }

    // SAFETY: No other invariants.
    unsafe { ffi::usb_start() };

    Ok(())
}

/// Check if interface `ticket` is ready to perform on selected `interest`.
///
/// Returns immediately, does not block. Useful for constructing event loops.
pub fn usb_poll(ticket: IfaceTicket, interest: Interest) -> Event {
    let ready = match ticket {
        IfaceTicket::Hid(iface_num) => match interest {
            Interest::Read => HidConfig::ready_to_read(iface_num),
            Interest::Write => HidConfig::ready_to_write(iface_num),
        },
        IfaceTicket::WebUsb(iface_num) => match interest {
            Interest::Read => WebUsbConfig::ready_to_read(iface_num),
            Interest::Write => WebUsbConfig::ready_to_write(iface_num),
        },
    };
    if ready {
        Event::Ready
    } else {
        Event::Pending
    }
}

/// Read a report from the interrupt interface specified by `ticket`.
///
/// Returns immediately, does not block. Returns the total number of bytes read,
/// which will always be the full length of `buffer`. Zero return value means
/// the resource is either not ready to read, or the `buffer` is too short for
/// the report. Caller should always take care to supply buffers longer or equal
/// to the length of the registered `rx_buffer`.
pub fn usb_read_report(ticket: IfaceTicket, buffer: &mut [u8]) -> Result<usize, UsbError> {
    match ticket {
        IfaceTicket::Hid(iface_num) => HidConfig::read(iface_num, buffer),
        IfaceTicket::WebUsb(iface_num) => WebUsbConfig::read(iface_num, buffer),
    }
}

/// Write a report to the interrupt interface specified by `ticket`.
///
/// Returns immediately, does not block. Returns the total number of bytes
/// written, which will always be the full length of `buffer`. Zero return value
/// means the resource is either not ready to write. Caller should not send
/// buffers larger than the configured maximum report size.
pub fn usb_write_report(ticket: IfaceTicket, buffer: &[u8]) -> Result<usize, UsbError> {
    match ticket {
        IfaceTicket::Hid(iface_num) => HidConfig::write(iface_num, buffer),
        IfaceTicket::WebUsb(iface_num) => WebUsbConfig::write(iface_num, buffer),
    }
}

/// Stop the USB communications and reset the stack.
///
/// Should be closed only with the USB running.
pub fn usb_close() {
    // SAFETY: No other invariants.
    unsafe {
        ffi::usb_stop();
        ffi::usb_deinit();
    };
}

const MAX_INTERFACE_COUNT: usize = 4;

#[derive(Default)]
pub struct UsbConfig<'a> {
    pub vendor_id: u16,
    pub product_id: u16,
    pub release_num: u16,
    pub manufacturer: &'static CStr,
    pub product: &'static CStr,
    pub interface: &'static CStr,
    pub serial_number: &'a CStr,
    pub usb21_landing: bool,
    pub interfaces: Vec<IfaceConfig, MAX_INTERFACE_COUNT>,
}

impl UsbConfig<'_> {
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
            interface: self.interface.as_ptr(),
            // Because we set the SN dynamically, we need to copy it to the static storage first.
            serial_number: set_global_serial_number(self.serial_number).as_ptr(),
            usb21_enabled: secbool::TRUE,
            usb21_landing: if self.usb21_landing {
                secbool::TRUE
            } else {
                secbool::FALSE
            },
        }
    }
}

/// Value used for reading or writing reports to a interrupt-report based USB
/// interface. Used for HID and WebUSB interfaces.
#[derive(Copy, Clone, Eq, PartialEq)]
pub enum IfaceTicket {
    Hid(u8),
    WebUsb(u8),
}

pub enum IfaceConfig {
    WebUsb(WebUsbConfig),
    Hid(HidConfig),
    Vcp(VcpConfig),
}

pub struct WebUsbConfig {
    pub rx_buffer: &'static mut [u8; 64],
    pub iface_num: u8,
    pub ep_in: u8,
    pub ep_out: u8,
    pub emu_port: u16,
}

impl WebUsbConfig {
    pub fn add(self, config: &mut UsbConfig) -> Result<IfaceTicket, UsbError> {
        let ticket = IfaceTicket::WebUsb(self.iface_num);
        config
            .interfaces
            .push(IfaceConfig::WebUsb(self))
            .map(|_| ticket)
            .map_err(|_| UsbError::FailedToAddInterface)
    }

    fn register(&mut self) -> Result<(), UsbError> {
        // SAFETY: We call this from `usb_open`, no other invariants.
        let res = unsafe { ffi::usb_webusb_add(&self.as_webusb_info()) };

        if res != secbool::TRUE {
            Err(UsbError::FailedToAddInterface)
        } else {
            Ok(())
        }
    }

    fn as_webusb_info(&mut self) -> ffi::usb_webusb_info_t {
        ffi::usb_webusb_info_t {
            rx_buffer: self.rx_buffer.as_mut_ptr(), // With length of max_packet_len bytes.
            max_packet_len: self.rx_buffer.len() as u8, /* Length of the biggest report and of
                                                     * rx_buffer. */
            iface_num: self.iface_num, // Address of this WebUSB interface.
            // emu_port: self.emu_port, // UDP port of this interface in the emulator.
            ep_in: self.ep_in, // Address of IN endpoint (with the highest bit set).
            ep_out: self.ep_out, // Address of OUT endpoint.
            subclass: 0,       // usb_iface_subclass_t
            protocol: 0,       // usb_iface_protocol_t
            polling_interval: 1, // In units of 1ms.
        }
    }

    fn ready_to_read(iface_num: u8) -> bool {
        // SAFETY: Safe operation.
        unsafe { ffi::usb_webusb_can_read(iface_num) == secbool::TRUE }
    }

    fn ready_to_write(iface_num: u8) -> bool {
        // SAFETY: Safe operation.
        unsafe { ffi::usb_webusb_can_write(iface_num) == secbool::TRUE }
    }

    fn read(iface_num: u8, buffer: &mut [u8]) -> Result<usize, UsbError> {
        // SAFETY: Safe operation, does not retain `buffer` and does not write outside
        // of it.
        let result =
            unsafe { ffi::usb_webusb_read(iface_num, buffer.as_mut_ptr(), buffer.len() as u32) };

        if result < 0 {
            Err(UsbError::InterfaceNotFound)
        } else {
            Ok(result as usize)
        }
    }

    fn write(iface_num: u8, buffer: &[u8]) -> Result<usize, UsbError> {
        // SAFETY: Safe operation, does not retain `buffer` and does not read outside of
        // it.
        let result =
            unsafe { ffi::usb_webusb_write(iface_num, buffer.as_ptr(), buffer.len() as u32) };

        if result < 0 {
            Err(UsbError::InterfaceNotFound)
        } else {
            Ok(result as usize)
        }
    }
}

pub struct HidConfig {
    pub report_desc: &'static [u8],
    pub rx_buffer: &'static mut [u8; 64],
    pub iface_num: u8,
    pub ep_in: u8,
    pub ep_out: u8,
    pub emu_port: u16,
}

impl HidConfig {
    pub fn add(self, config: &mut UsbConfig) -> Result<IfaceTicket, UsbError> {
        let ticket = IfaceTicket::Hid(self.iface_num);
        config
            .interfaces
            .push(IfaceConfig::Hid(self))
            .map(|_| ticket)
            .map_err(|_| UsbError::FailedToAddInterface)
    }

    fn register(&mut self) -> Result<(), UsbError> {
        // SAFETY: We call this from `usb_open`, no other invariants.
        let res = unsafe { ffi::usb_hid_add(&self.as_hid_info()) };

        if res != secbool::TRUE {
            Err(UsbError::FailedToAddInterface)
        } else {
            Ok(())
        }
    }

    fn as_hid_info(&mut self) -> ffi::usb_hid_info_t {
        ffi::usb_hid_info_t {
            report_desc: self.report_desc.as_ptr(), // With length of report_desc_len bytes.
            report_desc_len: self.report_desc.len() as u8, // Length of report_desc.
            rx_buffer: self.rx_buffer.as_mut_ptr(), // With length of max_packet_len bytes.
            max_packet_len: self.rx_buffer.len() as u8, /* Length of the biggest report and of
                                                     * rx_buffer. */
            iface_num: self.iface_num, // Address of this HID interface.
            // emu_port: self.emu_port, // UDP port of this interface in the emulator.
            ep_in: self.ep_in, // Address of IN endpoint (with the highest bit set).
            ep_out: self.ep_out, // Address of OUT endpoint.
            subclass: 0,       // usb_iface_subclass_t
            protocol: 0,       // usb_iface_protocol_t
            polling_interval: 1, // In units of 1ms.
        }
    }

    fn ready_to_read(iface_num: u8) -> bool {
        // SAFETY: Safe operation.
        unsafe { ffi::usb_hid_can_read(iface_num) == secbool::TRUE }
    }

    fn ready_to_write(iface_num: u8) -> bool {
        // SAFETY: Safe operation.
        unsafe { ffi::usb_hid_can_write(iface_num) == secbool::TRUE }
    }

    fn read(iface_num: u8, buffer: &mut [u8]) -> Result<usize, UsbError> {
        // SAFETY: Safe operation, does not retain `buffer` and does not write outside
        // of it.
        let result =
            unsafe { ffi::usb_hid_read(iface_num, buffer.as_mut_ptr(), buffer.len() as u32) };

        if result < 0 {
            Err(UsbError::InterfaceNotFound)
        } else {
            Ok(result as usize)
        }
    }

    fn write(iface_num: u8, buffer: &[u8]) -> Result<usize, UsbError> {
        // SAFETY: Safe operation, does not retain `buffer` and does not read outside of
        // it.
        let result = unsafe { ffi::usb_hid_write(iface_num, buffer.as_ptr(), buffer.len() as u32) };

        if result < 0 {
            Err(UsbError::InterfaceNotFound)
        } else {
            Ok(result as usize)
        }
    }
}

pub struct VcpConfig {
    pub rx_buffer: &'static mut [u8; 1024],
    pub tx_buffer: &'static mut [u8; 1024],
    pub rx_packet: &'static mut [u8; 64],
    pub tx_packet: &'static mut [u8; 64],
    pub rx_intr_fn: Option<unsafe extern "C" fn()>,
    pub rx_intr_byte: u8,
    pub iface_num: u8,
    pub data_iface_num: u8,
    pub ep_in: u8,
    pub ep_out: u8,
    pub ep_cmd: u8,
    pub emu_port: u16,
}

impl VcpConfig {
    pub fn add(self, config: &mut UsbConfig) -> Result<(), UsbError> {
        config
            .interfaces
            .push(IfaceConfig::Vcp(self))
            .map_err(|_| UsbError::FailedToAddInterface)
    }

    fn register(&mut self) -> Result<(), UsbError> {
        // SAFETY: We call this from `usb_open`, no other invariants.
        let res = unsafe { ffi::usb_vcp_add(&self.as_vcp_info()) };

        if res != secbool::TRUE {
            Err(UsbError::FailedToAddInterface)
        } else {
            Ok(())
        }
    }

    fn as_vcp_info(&mut self) -> ffi::usb_vcp_info_t {
        ffi::usb_vcp_info_t {
            tx_packet: self.tx_packet.as_mut_ptr(), /* Buffer for one packet, with length of at
                                                     * least max_packet_len bytes. */
            tx_buffer: self.tx_buffer.as_mut_ptr(), /* Buffer for IN EP ring buffer, with length
                                                     * of at least tx_buffer_len bytes. */
            rx_packet: self.rx_packet.as_mut_ptr(), /* Buffer for one packet, with length of at
                                                     * least max_packet_len bytes. */
            rx_buffer: self.rx_buffer.as_mut_ptr(), /* Buffer for OUT EP ring buffer, with length
                                                     * of at least rx_buffer_len bytes. */
            max_packet_len: self.rx_packet.len() as u8, /* Length of the biggest packet, and of
                                                         * tx_packet and rx_packet. */
            tx_buffer_len: self.tx_buffer.len(), // Length of tx_buffer, needs to be a power of 2.
            rx_buffer_len: self.rx_buffer.len(), // Length of rx_buffer, needs to be a power of 2.
            rx_intr_fn: self.rx_intr_fn,         /* Callback called from usb_vcp_class_data_out
                                                  * IRQ handler if rx_intr_byte matches. */
            rx_intr_byte: self.rx_intr_byte, // Value matched against every received byte.
            iface_num: self.iface_num,       // Address of this VCP interface.
            data_iface_num: self.data_iface_num, /* Address of data interface of the VCP interface
                                              * association. */
            // emu_port: self.emu_port,  // UDP port of this interface in the emulator.
            ep_cmd: self.ep_cmd, // Address of IN CMD endpoint (with the highest bit set).
            ep_in: self.ep_in,   // Address of IN endpoint (with the highest bit set).
            ep_out: self.ep_out, // Address of OUT endpoint.
            polling_interval: 10, // In units of 1ms.
        }
    }
}

#[cfg(test)]
mod tests {
    use cstr_core::cstr;

    use super::*;

    #[test]
    fn test_usb() {
        // Example port of usb.py.

        const UDP_PORT: u16 = 0;
        const WIRE_PORT_OFFSET: u16 = 0;
        const DEBUGLINK_PORT_OFFSET: u16 = 1;
        const WEBAUTHN_PORT_OFFSET: u16 = 2;
        const VCP_PORT_OFFSET: u16 = 3;

        let mut iface_iter = 0u8..;

        const ENABLE_IFACE_DEBUG: bool = true;
        const ENABLE_IFACE_WEBAUTHN: bool = true;
        const ENABLE_IFACE_VCP: bool = true;

        let mut config = UsbConfig {
            vendor_id: 0x1209,
            product_id: 0x53C1,
            release_num: 0x0200,
            manufacturer: cstr!("SatoshiLabs"),
            product: cstr!("TREZOR"),
            serial_number: cstr!(""),
            interface: cstr!("TREZOR Interface"),
            usb21_landing: false,
            ..UsbConfig::default()
        };

        let id_wire = iface_iter.next().unwrap();
        let iface_wire = WebUsbConfig {
            rx_buffer: &mut [0; 64],
            iface_num: id_wire,
            ep_in: 0x81 + id_wire,
            ep_out: 0x01 + id_wire,
            emu_port: UDP_PORT + WIRE_PORT_OFFSET,
        };
        let ticket_wire = iface_wire.add(&mut config).unwrap();

        if ENABLE_IFACE_DEBUG {
            let id_debug = iface_iter.next().unwrap();
            let iface_debug = WebUsbConfig {
                rx_buffer: &mut [0; 64],
                iface_num: id_debug,
                ep_in: 0x81 + id_debug,
                ep_out: 0x01 + id_debug,
                emu_port: UDP_PORT + DEBUGLINK_PORT_OFFSET,
            };
            let ticket_debug = iface_debug.add(&mut config).unwrap();
        }

        if ENABLE_IFACE_WEBAUTHN {
            let id_webauthn = iface_iter.next().unwrap();
            let iface_webauthn = HidConfig {
                report_desc: &[
                    0x06, 0xd0, 0xf1, // USAGE_PAGE (FIDO Alliance)
                    0x09, 0x01, // USAGE (U2F HID Authenticator Device)
                    0xa1, 0x01, // COLLECTION (Application)
                    0x09, 0x20, // USAGE (Input Report Data)
                    0x15, 0x00, // LOGICAL_MINIMUM (0)
                    0x26, 0xff, 0x00, // LOGICAL_MAXIMUM (255)
                    0x75, 0x08, // REPORT_SIZE (8)
                    0x95, 0x40, // REPORT_COUNT (64)
                    0x81, 0x02, // INPUT (Data,Var,Abs)
                    0x09, 0x21, // USAGE (Output Report Data)
                    0x15, 0x00, // LOGICAL_MINIMUM (0)
                    0x26, 0xff, 0x00, // LOGICAL_MAXIMUM (255)
                    0x75, 0x08, // REPORT_SIZE (8)
                    0x95, 0x40, // REPORT_COUNT (64)
                    0x91, 0x02, // OUTPUT (Data,Var,Abs)
                    0xc0, // END_COLLECTION
                ],
                rx_buffer: &mut [0; 64],
                iface_num: id_webauthn,
                ep_in: 0x81 + id_webauthn,
                ep_out: 0x01 + id_webauthn,
                emu_port: UDP_PORT + WEBAUTHN_PORT_OFFSET,
            };
            let ticket_webauthn = iface_webauthn.add(&mut config).unwrap();
        }

        if ENABLE_IFACE_VCP {
            let id_vcp = iface_iter.next().unwrap();
            let id_vcp_data = iface_iter.next().unwrap();
            let iface_vcp = VcpConfig {
                rx_buffer: &mut [0; 1024],
                tx_buffer: &mut [0; 1024],
                rx_packet: &mut [0; 64],
                tx_packet: &mut [0; 64],
                rx_intr_fn: None, // Use pendsv_kbd_intr here.
                rx_intr_byte: 3,  // Ctrl-C
                iface_num: id_vcp,
                data_iface_num: id_vcp_data,
                ep_in: 0x81 + id_vcp,
                ep_out: 0x01 + id_vcp,
                ep_cmd: 0x81 + id_vcp_data,
                emu_port: UDP_PORT + VCP_PORT_OFFSET,
            };
            iface_vcp.add(&mut config).unwrap();
        }

        usb_open(config).unwrap();
        usb_close();
    }
}

fn set_global_serial_number(sn: &CStr) -> &'static CStr {
    static mut GLOBAL_BUFFER: [u8; 64] = [0; 64];

    // SAFETY: We are in a single threaded context, so the only possible race on
    // `GLOBAL_BUFFER` is with the USB stack. We should take care to only call
    // `set_global_serial_number` with the USB stopped.
    unsafe {
        let sn_nul = sn.to_bytes_with_nul();

        // Panics if `sn_nul` is bigger then `GLOBAL_BUFFER`.
        GLOBAL_BUFFER[..sn_nul.len()].copy_from_slice(sn_nul);

        CStr::from_bytes_with_nul_unchecked(&GLOBAL_BUFFER[..sn_nul.len()])
    }
}
