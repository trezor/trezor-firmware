use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("usb/inc");

    lib.add_define("USE_USB", Some("1"));

    if cfg!(feature = "usb_iface_wire") {
        lib.add_define("USE_USB_IFACE_WIRE", Some("1"));
    }

    if cfg!(feature = "usb_iface_debug") {
        lib.add_define("USE_USB_IFACE_DEBUG", Some("1"));
        lib.add_define("DEBUGLINK", Some("1"));
    }

    if cfg!(feature = "usb_iface_webauthn") {
        lib.add_define("USE_USB_IFACE_WEBAUTHN", Some("1"));
    }

    if cfg!(feature = "usb_iface_vcp") {
        lib.add_define("USE_USB_IFACE_VCP", Some("1"));
    }

    if cfg!(feature = "ward_service_channel") {
        lib.add_define("USE_WARD_SERVICE_CHANNEL", Some("1"));
        // An interface beside the wire one needs a WinUSB compatible ID, so compile in the
        // machinery that can advertise a second interface to Windows. Kept as its own define
        // rather than reusing USE_WARD_SERVICE_CHANNEL inside the generic USB code: the
        // capability is "one more interface needs WinUSB", not "WARD exists", and the bootloader
        // -- which is within a few hundred bytes of its flash budget -- must not pay for it.
        lib.add_define("USE_USB_WINUSB_EXTRA_IFACE", Some("1"));
    }

    if cfg!(feature = "emulator") {
        lib.add_sources(["usb/unix/sock.c", "usb/unix/usb.c", "usb/usb_config.c"]);
    } else if cfg!(feature = "mcu_stm32") {
        lib.add_sources([
            "usb/stm32/usb_class_hid.c",
            "usb/stm32/usb_class_vcp.c",
            "usb/stm32/usb_class_webusb.c",
            "usb/stm32/usb.c",
            "usb/stm32/usb_rbuf.c",
            "usb/stm32/usbd_conf.c",
            "usb/stm32/usbd_core.c",
            "usb/stm32/usbd_ctlreq.c",
            "usb/stm32/usbd_ioreq.c",
            "usb/usb_config.c",
        ]);
    } else {
        bail_unsupported!();
    }

    Ok(())
}
