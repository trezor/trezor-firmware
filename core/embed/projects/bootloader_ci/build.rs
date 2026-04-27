use xbuild::Result;

fn main() -> Result<()> {
    xbuild::build_and_link("bootloader", |lib| {
        lib.import_lib("io")?;

        lib.add_includes([".", "protob"]);

        lib.add_sources([
            "bootui.c",
            "main.c",
            "messages.c",
            "version_check.c",
            "protob/pb/messages.pb.c",
        ]);

        if cfg!(not(feature = "emulator")) {
            if cfg!(feature = "boot_ucb") {
                lib.add_source("../bootloader/header_pq.c");
            } else {
                lib.add_source("../bootloader/header.S");
            }
        }

        if cfg!(feature = "emulator") {
            lib.add_source("emulator.c");
        }

        let nanopb_dir = "../../../vendor/nanopb";
        lib.add_include(nanopb_dir);
        lib.add_sources_from_folder(nanopb_dir, ["pb_common.c", "pb_decode.c", "pb_encode.c"]);

        Ok(())
    })
}
