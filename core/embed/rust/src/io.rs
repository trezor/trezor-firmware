use core::ops::RangeFrom;

use cstr_core::{cstr, CStr};

use crate::{
    error::Error,
    micropython::{buffer::Buffer, obj::Obj},
    time::{Duration, Instant},
    trezorhal::usb::{
        usb_is_ready_to_read, usb_is_ready_to_write, usb_open, IfaceTicket, UsbConfig, UsbError,
        WebUsbConfig,
    },
    util,
    util::wait_in_busy_loop,
};

mod ffi {
    extern "C" {
        #[cfg(feature = "model_t1")]
        pub fn button_read() -> u32;
        #[cfg(feature = "model_tt")]
        pub fn touch_read() -> u32;
    }
}

#[cfg(feature = "model_t1")]
pub fn button_read() -> u32 {
    unsafe { ffi::button_read() }
}

#[cfg(feature = "model_tt")]
pub fn touch_read() -> u32 {
    unsafe { ffi::touch_read() }
}

pub enum Resource {
    #[cfg(feature = "model_t1")]
    Button,
    #[cfg(feature = "model_tt")]
    Touch,
    UsbRead(IfaceTicket),
    UsbWrite(IfaceTicket),
}

pub enum Event {
    #[cfg(feature = "model_t1")]
    Button(u32), // TODO: We should somehow use `ButtonEvent` from UI here.
    #[cfg(feature = "model_tt")]
    Touch(u32), // TODO: We should somehow use `TouchEvent` from UI here.
    UsbRead(IfaceTicket),
    UsbWrite(IfaceTicket),
    TimedOut,
}

pub fn poll_io(resources: &[Resource], timeout: Duration) -> Result<Event, Error> {
    let deadline = Instant::now()
        .checked_add(timeout)
        .ok_or(Error::OutOfRange)?;

    loop {
        // Poll all resources, return if ready.
        for resource in resources {
            match resource {
                #[cfg(feature = "model_t1")]
                Resource::Button => {
                    let event = button_read();
                    if event != 0 {
                        return Ok(Event::Button(event));
                    }
                }
                #[cfg(feature = "model_tt")]
                Resource::Touch => {
                    let event = touch_read();
                    if event != 0 {
                        return Ok(Event::Touch(event));
                    }
                }
                Resource::UsbRead(ticket) => {
                    if usb_is_ready_to_read(*ticket) {
                        return Ok(Event::UsbRead(*ticket));
                    }
                }
                Resource::UsbWrite(ticket) => {
                    if usb_is_ready_to_write(*ticket) {
                        return Ok(Event::UsbWrite(*ticket));
                    }
                }
            }
        }

        // No resource is ready yet, wait or exit on timeout.
        if Instant::now() < deadline {
            wait_in_busy_loop();
        } else {
            return Ok(Event::TimedOut);
        }
    }
}

extern "C" fn io_usb_start(serial_number: Obj) -> Obj {
    #[cfg(feature = "ui_debug")]
    use crate::trezorhal::usb::VcpConfig;

    #[cfg(not(feature = "bitcoin_only"))]
    use crate::trezorhal::usb::HidConfig;

    // SAFETY:
    // In this function we often take mut refs to static mut buffers. This requires
    // an unsafe block. Safety rationale:
    //  - We are in a single-threaded context.
    //  - `io_usb_start` is required to be called with USB turned off.
    //  - Underlying USB stack is required to manage the buffers on its own,
    //    guarding i.e. against escaping of stale buffer content.

    const UDP_PORT: u16 = 0;
    const WIRE_PORT_OFFSET: u16 = 0;
    const DEBUGLINK_PORT_OFFSET: u16 = 1;
    const WEBAUTHN_PORT_OFFSET: u16 = 2;
    const VCP_PORT_OFFSET: u16 = 3;

    fn usb_config(serial_number: &CStr) -> UsbConfig {
        UsbConfig {
            vendor_id: 0x1209,
            product_id: 0x53C1,
            release_num: 0x0200,
            manufacturer: cstr!("SatoshiLabs"),
            product: cstr!("TREZOR"),
            serial_number: set_global_serial_number(serial_number),
            interface: cstr!("TREZOR Interface"),
            usb21_landing: false,
            ..UsbConfig::default()
        }
    }

    fn create_wire_iface(ids: &mut RangeFrom<u8>) -> WebUsbConfig {
        static mut WIRE_RX_BUFFER: [u8; 64] = [0; 64];

        let id = ids.next().unwrap();
        WebUsbConfig {
            rx_buffer: unsafe { &mut WIRE_RX_BUFFER },
            iface_num: id,
            ep_in: 0x81 + id,
            ep_out: 0x01 + id,
            emu_port: UDP_PORT + WIRE_PORT_OFFSET,
        }
    }

    #[cfg(feature = "ui_debug")]
    fn create_debug_iface(ids: &mut RangeFrom<u8>) -> WebUsbConfig {
        static mut DEBUG_RX_BUFFER: [u8; 64] = [0; 64];

        let id = ids.next().unwrap();
        WebUsbConfig {
            rx_buffer: unsafe { &mut DEBUG_RX_BUFFER },
            iface_num: id,
            ep_in: 0x81 + id,
            ep_out: 0x01 + id,
            emu_port: UDP_PORT + DEBUGLINK_PORT_OFFSET,
        }
    }

    #[cfg(not(feature = "bitcoin_only"))]
    fn create_webauthn_iface(ids: &mut RangeFrom<u8>) -> HidConfig {
        static mut WEBAUTHN_RX_BUFFER: [u8; 64] = [0; 64];

        let id = ids.next().unwrap();
        HidConfig {
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
            rx_buffer: unsafe { &mut WEBAUTHN_RX_BUFFER },
            iface_num: id,
            ep_in: 0x81 + id,
            ep_out: 0x01 + id,
            emu_port: UDP_PORT + WEBAUTHN_PORT_OFFSET,
        }
    }

    #[cfg(feature = "ui_debug")]
    fn create_vcp_iface(ids: &mut RangeFrom<u8>) -> VcpConfig {
        static mut VCP_RX_BUFFER: [u8; 1024] = [0; 1024];
        static mut VCP_TX_BUFFER: [u8; 1024] = [0; 1024];
        static mut VCP_RX_PACKET: [u8; 64] = [0; 64];
        static mut VCP_TX_PACKET: [u8; 64] = [0; 64];

        let id = ids.next().unwrap();
        let id_data = ids.next().unwrap();
        VcpConfig {
            rx_buffer: unsafe { &mut VCP_RX_BUFFER },
            tx_buffer: unsafe { &mut VCP_TX_BUFFER },
            rx_packet: unsafe { &mut VCP_RX_PACKET },
            tx_packet: unsafe { &mut VCP_TX_PACKET },
            rx_intr_fn: None, // Use pendsv_kbd_intr here.
            rx_intr_byte: 3,  // Ctrl-C
            iface_num: id,
            data_iface_num: id_data,
            ep_in: 0x81 + id,
            ep_out: 0x01 + id,
            ep_cmd: 0x81 + id_data,
            emu_port: UDP_PORT + VCP_PORT_OFFSET,
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

    let block = || {
        let serial_number: Buffer = serial_number.try_into()?;
        let serial_number =
            CStr::from_bytes_with_nul(&serial_number).map_err(|_| Error::TypeError)?;

        let mut ids = 0u8..; // Iterator of interface IDS.
        let mut usb = usb_config(serial_number);

        // Create the interfaces we use and add them to the config. Note that the order
        // matters.

        let wire_id = create_wire_iface(&mut ids).add(&mut usb)?.iface_num();

        #[cfg(feature = "ui_debug")]
        let debug_id = Some(create_debug_iface(&mut ids).add(&mut usb)?.iface_num());
        #[cfg(not(feature = "ui_debug"))]
        let debug_id: Option<u8> = None;

        #[cfg(feature = "bitcoin_only")]
        let webauthn_id: Option<u8> = None;
        #[cfg(not(feature = "bitcoin_only"))]
        let webauthn_id = Some(create_webauthn_iface(&mut ids).add(&mut usb)?.iface_num());

        #[cfg(feature = "ui_debug")]
        let vcp_id = {
            let vcp = create_vcp_iface(&mut ids);
            let vcp_id = vcp.iface_num;
            vcp.add(&mut usb)?;
            vcp_id
        };

        // Convert used interface IDs to MicroPython objects.
        let wire_id_obj = Obj::try_from(wire_id as u32)?;
        let debug_id_obj = Obj::from(debug_id.map(Obj::try_from).transpose()?);
        let webauthn_id_obj = Obj::from(webauthn_id.map(Obj::try_from).transpose()?);
        let tuple = Obj::try_from((wire_id_obj, debug_id_obj, webauthn_id_obj))?;

        // Initialize the USB and start the configured interfaces.
        usb_open(usb)?;

        // Enable VCP support in MicroPython.
        #[cfg(feature = "ui_debug")]
        {
            extern "C" {
                fn mp_hal_set_vcp_iface(iface_num: cty::c_int);
            }
            mp_hal_set_cvp_iface(vcp_id);
        }

        Ok(tuple)
    };
    unsafe { util::try_or_raise(block) }
}

impl From<UsbError> for Error {
    fn from(usb: UsbError) -> Self {
        match usb {
            UsbError::FailedToAddInterface => Error::ValueError(cstr!("Failed to add interface")),
            UsbError::InterfaceNotFound => Error::ValueError(cstr!("Interface not found")),
        }
    }
}
