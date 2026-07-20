use xbuild::{CLibrary, Result, bail_unsupported};

pub fn def_module(lib: &mut CLibrary) -> Result<()> {
    lib.add_include("nfc/inc");

    lib.add_define("USE_NFC", Some("1"));

    if cfg!(feature = "emulator") {
        // No sources for the emulator
    } else if cfg!(feature = "nfc_st25r200") {
        lib.add_sources_with_attrs(
            [
                "nfc/st25/nfc.c",
                "nfc/st25/ndef.c",
                "nfc/st25/card_emulation.c",
                "nfc/st25/rfal004/source/rfal_analogConfig.c",
                "nfc/st25/rfal004/source/rfal_nfc.c",
                "nfc/st25/rfal004/source/rfal_nfca.c",
                "nfc/st25/rfal004/source/rfal_nfcb.c",
                "nfc/st25/rfal004/source/rfal_nfcf.c",
                "nfc/st25/rfal004/source/rfal_nfcv.c",
                "nfc/st25/rfal004/source/rfal_isoDep.c",
                "nfc/st25/rfal004/source/rfal_nfcDep.c",
                "nfc/st25/rfal004/source/rfal_st25tb.c",
                "nfc/st25/rfal004/source/rfal_t1t.c",
                "nfc/st25/rfal004/source/rfal_t2t.c",
                "nfc/st25/rfal004/source/rfal_iso15693_2.c",
                "nfc/st25/rfal004/source/rfal_crc.c",
                "nfc/st25/rfal004/source/rfal_dpo.c",
                "nfc/st25/rfal004/source/st25r200/rfal_rfst25r200.c",
                "nfc/st25/rfal004/source/st25r200/st25r200.c",
                "nfc/st25/rfal004/source/st25r200/st25r200_com.c",
                "nfc/st25/rfal004/source/st25r200/st25r200_irq.c",
            ],
            Some(
                xbuild::CompileAttrs::new()
                    .with_include("nfc/st25/")
                    .with_include("nfc/st25/rfal004/source")
                    .with_include("nfc/st25/rfal004/source/st25r200")
                    .with_include("nfc/st25/rfal004/include/"),
            ),
        );
    } else if cfg!(feature = "nfc_st25r210") {
        lib.add_sources_with_attrs(
            [
                "nfc/st25/nfc.c",
                "nfc/st25/ndef.c",
                "nfc/st25/card_emulation.c",
                "nfc/st25/rfal005/source/rfal_analogConfig.c",
                "nfc/st25/rfal005/source/rfal_nfc.c",
                "nfc/st25/rfal005/source/rfal_nfca.c",
                "nfc/st25/rfal005/source/rfal_nfcb.c",
                "nfc/st25/rfal005/source/rfal_nfcf.c",
                "nfc/st25/rfal005/source/rfal_nfcv.c",
                "nfc/st25/rfal005/source/rfal_isoDep.c",
                "nfc/st25/rfal005/source/rfal_nfcDep.c",
                "nfc/st25/rfal005/source/rfal_st25tb.c",
                "nfc/st25/rfal005/source/rfal_t1t.c",
                "nfc/st25/rfal005/source/rfal_t2t.c",
                "nfc/st25/rfal005/source/rfal_iso15693_2.c",
                "nfc/st25/rfal005/source/rfal_crc.c",
                "nfc/st25/rfal005/source/rfal_dpo.c",
                "nfc/st25/rfal005/source/st25r500/rfal_rfst25r500.c",
                "nfc/st25/rfal005/source/st25r500/st25r500.c",
                "nfc/st25/rfal005/source/st25r500/st25r500_com.c",
                "nfc/st25/rfal005/source/st25r500/st25r500_dpocr.c",
                "nfc/st25/rfal005/source/st25r500/st25r500_irq.c",
            ],
            Some(
                xbuild::CompileAttrs::new()
                    .with_include("nfc/st25/")
                    .with_include("nfc/st25/rfal005/source")
                    .with_include("nfc/st25/rfal005/source/st25r500")
                    .with_include("nfc/st25/rfal005/include/"),
            ),
        );
    } else {
        bail_unsupported!();
    }

    Ok(())
}
