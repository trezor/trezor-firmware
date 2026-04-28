use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("nfc/inc");

    lib.add_define("USE_NFC", Some("1"));

    if cfg!(feature = "emulator") {
        // No sources for the emulator
    } else if cfg!(feature = "mcu_stm32u5") {
        lib.add_sources_with_attrs([
        "nfc/st25/nfc.c",
        "nfc/st25/ndef.c",
        "nfc/st25/card_emulation.c",
        "nfc/st25/rfal002/source/st25r3916/rfal_rfst25r3916.c",
        "nfc/st25/rfal002/source/rfal_analogConfig.c",
        "nfc/st25/rfal002/source/rfal_nfc.c",
        "nfc/st25/rfal002/source/rfal_nfca.c",
        "nfc/st25/rfal002/source/rfal_nfcb.c",
        "nfc/st25/rfal002/source/rfal_nfcf.c",
        "nfc/st25/rfal002/source/rfal_nfcv.c",
        "nfc/st25/rfal002/source/rfal_isoDep.c",
        "nfc/st25/rfal002/source/rfal_nfcDep.c",
        "nfc/st25/rfal002/source/rfal_st25tb.c",
        "nfc/st25/rfal002/source/rfal_t1t.c",
        "nfc/st25/rfal002/source/rfal_t2t.c",
        "nfc/st25/rfal002/source/rfal_iso15693_2.c",
        "nfc/st25/rfal002/source/rfal_crc.c",
        "nfc/st25/rfal002/source/st25r3916/st25r3916.c",
        "nfc/st25/rfal002/source/st25r3916/st25r3916_com.c",
        "nfc/st25/rfal002/source/st25r3916/st25r3916_led.c",
        "nfc/st25/rfal002/source/st25r3916/st25r3916_irq.c",
        ],
        Some(xbuild::CompileAttrs::new()
            .with_include("nfc/st25/")
            .with_include("nfc/st25/rfal002/source")
            .with_include("nfc/st25/rfal002/source/st25r3916")
            .with_include("nfc/st25/rfal002/include/")
        )
    );
    } else {
        bail_unsupported!();
    }

    Ok(())
}
